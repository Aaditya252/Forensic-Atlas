"""Bounded summary selection and persistence tests; no model needed."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import backend.app as api
from backend.agents.case_summary import generate_summary, prepare_context
from backend.local_llm import ModelError
from test_context_agents import FakeGraph, FIXTURE


class SummaryGraph(FakeGraph):
    def list_entities(self, limit=40):
        return [{"id": "SES-0942", "label": "Session"}]


class SelectionModel:
    def __init__(self, invalid=False):
        self.invalid = invalid
        self.calls = 0

    def model_info(self):
        return {"modelId": "test-double", "trainedByUs": False}

    def status(self):
        return {"ready": True}

    def select_facts(self, messages, ids, groups=None):
        self.calls += 1
        facts = prepare_context(FIXTURE, SummaryGraph())["facts"]
        selected = [facts[0]["factId"], next(f["factId"] for f in facts if f["origin"] == "review-record")]
        return {"selection": {"selectedFactIds": ["F999"] if self.invalid else selected}}


class SummaryTests(unittest.TestCase):
    def test_selected_statements_are_exact_source_cards(self):
        result = generate_summary(FIXTURE, SummaryGraph(), SelectionModel())
        cards = {f["factId"]: f for f in result["inputContext"]["facts"]}
        self.assertTrue(result["verification"]["ok"])
        for statement in result["statements"]:
            self.assertEqual(statement, cards[statement["factId"]])
        self.assertEqual(result["status"], "draft")

    def test_unknown_selection_rejected_after_two_attempts(self):
        model = SelectionModel(invalid=True)
        with self.assertRaises(ModelError) as caught:
            generate_summary(FIXTURE, SummaryGraph(), model)
        self.assertEqual(caught.exception.code, "SUMMARY_VERIFICATION_FAILED")
        self.assertEqual(model.calls, 2)

    def test_unknown_entity_rejected(self):
        with self.assertRaises(ModelError):
            prepare_context(FIXTURE, SummaryGraph(), "OTHER-CASE")

    def test_persistence_idempotency_and_request_conflict(self):
        from fastapi import HTTPException
        with tempfile.TemporaryDirectory(dir=api.ROOT) as temp:
            graph, model = SummaryGraph(), SelectionModel()
            with patch.object(api, "DB_PATH", Path(temp)/"case.sqlite3"), patch.object(api, "CaseGraph", return_value=graph), patch.object(api, "LocalLLM", return_value=model):
                api.initialize(seed_demo=True)
                first = api.create_case_summary("DF-24-017", {}, "summary-test")
                self.assertEqual(first, api.create_case_summary("DF-24-017", {}, "summary-test"))
                self.assertEqual(model.calls, 1)
                self.assertEqual(len(graph.episodes), 1)
                with self.assertRaises(HTTPException) as caught:
                    api.create_case_summary("DF-24-017", {"entityId":"SES-0942"}, "summary-test")
                self.assertEqual(caught.exception.status_code, 409)
                with api.connect() as db:
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM audit_events WHERE action='agent.case_summary_created'").fetchone()[0], 1)
                    db.execute("DELETE FROM idempotency_keys")
                # Graph recovery must not require model availability.
                model.status = lambda: {"ready": False}
                self.assertEqual(first, api.create_case_summary("DF-24-017", {}, "summary-test"))
                self.assertEqual(model.calls, 1)


if __name__ == "__main__":
    unittest.main()
