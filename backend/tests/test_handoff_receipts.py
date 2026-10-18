"""Receipt acknowledgement stays separate from task execution and evidence review."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
import backend.app as api

FIRST = "HO-" + "a"*24
SECOND = "HO-" + "b"*24


class ReceiptGraph:
    available = True

    def __init__(self):
        self.calls, self.saved = 0, {}

    def acknowledge_handoff(self, handoff_id, expected_version, key):
        self.calls += 1
        if key in self.saved:
            return self.saved[key]
        if expected_version != 1:
            return None
        result = {"id":handoff_id, "status":"acknowledged", "version":2, "acknowledgedAt":"2026-10-18T10:00:00Z"}
        self.saved[key] = result
        return result


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=api.ROOT)
        self.graph = ReceiptGraph()
        self.db_patch = patch.object(api, "DB_PATH", Path(self.temp.name)/"case.sqlite3")
        self.graph_patch = patch.object(api, "CaseGraph", return_value=self.graph)
        self.db_patch.start()
        self.graph_patch.start()
        api.initialize(seed_demo=True)

    def tearDown(self):
        self.graph_patch.stop()
        self.db_patch.stop()
        self.temp.cleanup()

    def ack(self, body=None, key="receipt-test", handoff=FIRST):
        return api.acknowledge_agent_handoff("DF-24-017", handoff, {"expectedVersion":1} if body is None else body, key)

    def test_receipt_replay_writes_one_audit_and_no_review_decision(self):
        first = self.ack()
        self.assertEqual(first, self.ack())
        self.assertEqual(self.graph.calls, 1)
        with api.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM audit_events WHERE action='agent.handoff_acknowledged'").fetchone()[0],1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM review_decisions").fetchone()[0],0)

    def test_same_key_for_other_handoff_conflicts(self):
        self.ack()
        with self.assertRaises(HTTPException) as caught:
            self.ack(handoff=SECOND)
        self.assertEqual(caught.exception.status_code,409)

    def test_same_key_for_other_version_conflicts(self):
        self.ack()
        with self.assertRaises(HTTPException) as caught:
            self.ack({"expectedVersion":2})
        self.assertEqual(caught.exception.status_code,409)

    def test_stale_version_conflicts(self):
        with self.assertRaises(HTTPException) as caught:
            self.ack({"expectedVersion":4})
        self.assertEqual(caught.exception.detail["code"],"HANDOFF_VERSION_CONFLICT")

    def test_invalid_body_and_missing_key_rejected(self):
        for body in ({"expectedVersion":True}, {"expectedVersion":1,"approved":True}, {}):
            with self.assertRaises(HTTPException) as caught:
                self.ack(body)
            self.assertEqual(caught.exception.status_code,422)
        with self.assertRaises(HTTPException) as caught:
            self.ack(key=None)
        self.assertEqual(caught.exception.status_code,400)

    def test_graph_unavailable_does_not_save_receipt(self):
        self.graph.available = False
        with self.assertRaises(HTTPException) as caught:
            self.ack()
        self.assertEqual(caught.exception.status_code,503)
        with api.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM idempotency_keys").fetchone()[0],0)
