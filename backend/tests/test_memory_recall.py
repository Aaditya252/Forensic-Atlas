import copy
import unittest

from backend.agents.memory_recall import recall_episodes, episode_detail
from backend.graph_store import CaseGraph
from test_agent_graph_memory import _FakeGraph


def episode(identifier="EP-1", case_id="CASE-A", source="ART-001"):
    return {"id": identifier, "caseId": case_id, "agentId": "case-summary", "kind": "case-summary", "summary": "Saved draft",
            "evidenceState": "candidate", "sourceIds": [source], "createdAt": "2026-10-18T10:00:00Z",
            "payload": {"answer": "Candidate DOWNLOADED relationship ART-001", "statements": [{"text": "Candidate path ART-001", "state":"candidate", "sources":[source]}], "inputContext":{"trace":[{"tool":"graph.explain_entity"}]}}}


class MemoryRecallTests(unittest.TestCase):
    def recall(self, rows, **kwargs):
        return recall_episodes(rows, case_id="CASE-A", known_sources={"ART-001"}, **kwargs)

    def test_requires_all_terms_and_returns_matched_fields(self):
        result = self.recall([episode()], query="downloaded ART-001")
        self.assertEqual(len(result["items"]), 1)
        self.assertIn("answer", result["items"][0]["matchedFields"])
        self.assertEqual(self.recall([episode()], query="downloaded missing")["items"], [])

    def test_cross_case_and_unknown_source_are_excluded(self):
        self.assertEqual(self.recall([episode(case_id="CASE-B"), episode(source="ART-999")])["items"], [])
        with self.assertRaises(ValueError):
            self.recall([episode()], source_id="ART-999")

    def test_window_and_output_are_bounded(self):
        result = self.recall([episode("EP-"+str(i)) for i in range(150)], limit=500)
        self.assertEqual(result["scannedCount"], 100)
        self.assertEqual(len(result["items"]), 20)
        self.assertTrue(result["windowMayBeTruncated"])

    def test_untrusted_search_is_only_text(self):
        self.assertEqual(self.recall([episode()], query="MATCH DETACH DELETE")["items"], [])
        with self.assertRaises(ValueError):
            self.recall([episode()], query="x"*161)

    def test_detail_retains_candidate_and_trace_without_mutation(self):
        row = episode()
        original = copy.deepcopy(row)
        detail = episode_detail(row, {"ART-001"})
        self.assertEqual(detail["evidenceState"], "candidate")
        self.assertEqual(detail["memoryKind"], "episodic_unverified")
        self.assertEqual(detail["trace"][0]["tool"], "graph.explain_entity")
        self.assertEqual(row, original)

    def test_episode_query_is_parameterized_and_case_scoped(self):
        graph = CaseGraph.__new__(CaseGraph)
        graph.case_id, graph.graph = "CASE-A", _FakeGraph()
        self.assertIsNone(graph.get_episode("EP-1"))
        query, params = graph.graph.calls[0]
        self.assertIn("caseId:$caseId,id:$id", query)
        self.assertEqual(params, {"caseId":"CASE-A", "id":"EP-1"})
        with self.assertRaises(ValueError):
            graph.get_episode("x') DELETE")
