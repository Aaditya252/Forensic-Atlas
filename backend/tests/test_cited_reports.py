import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
import backend.app as api
from backend.agents.case_summary import generate_summary
from backend.reporting import build_report, content_digest, render_html
from test_case_summary import FIXTURE, SummaryGraph, SelectionModel


def summary_episode():
    payload = generate_summary(FIXTURE, SummaryGraph(), SelectionModel())
    payload.update(caseId="DF-24-017", summaryId="SUM-test", createdAt="2026-10-18T10:00:00Z")
    return {"id":"EP-test", "caseId":"DF-24-017", "agentId":"case-summary", "payload":payload}


class ReportTests(unittest.TestCase):
    def build(self, episode=None, title="Case report"):
        return build_report(FIXTURE, episode or summary_episode(), report_id="RPT-test", title=title, created_at="2026-10-18T11:00:00Z")

    def test_exact_content_and_detached_snapshot(self):
        episode = summary_episode()
        envelope = self.build(episode)
        self.assertEqual(envelope["report"]["statements"], episode["payload"]["statements"])
        episode["payload"]["statements"][0]["text"] = "changed"
        self.assertNotEqual(envelope["report"]["statements"], episode["payload"]["statements"])
        self.assertEqual(envelope["contentSha256"], content_digest(envelope["report"]))

    def test_modified_statement_or_context_rejected(self):
        for target in ("statements", "inputContext"):
            episode = summary_episode()
            if target == "statements":
                # Detach so modifying a selection cannot also modify its source card.
                episode["payload"][target] = copy.deepcopy(episode["payload"][target])
                episode["payload"][target][0]["text"] += " unsupported"
            else:
                episode["payload"][target]["scope"] = "changed"
            with self.assertRaises(ValueError):
                self.build(episode)

    def test_cross_case_summary_rejected(self):
        episode = summary_episode()
        episode["caseId"] = "OTHER-CASE"
        with self.assertRaises(ValueError):
            self.build(episode)

    def test_html_escapes_title_and_has_draft_label(self):
        html = render_html(self.build(title='<script>alert("x")</script>'))
        self.assertNotIn('<script>',html)
        self.assertIn('&lt;script&gt;',html)
        self.assertIn('UNREVIEWED DRAFT',html)
        self.assertIn('ART-028',html)

    def test_api_save_replay_exports_offline_and_integrity_failure(self):
        episode = summary_episode()
        graph = SummaryGraph()
        graph.get_episode = lambda identifier: episode if identifier == "EP-test" else None
        with tempfile.TemporaryDirectory(dir=api.ROOT) as temp:
            with patch.object(api,"DB_PATH",Path(temp)/"case.sqlite3"), patch.object(api,"CaseGraph",return_value=graph):
                api.initialize(seed_demo=True)
                body = {"title":"Case report", "summaryEpisodeId":"EP-test"}
                first = api.create_cited_report("DF-24-017",body,"report-test")
                self.assertEqual(first,api.create_cited_report("DF-24-017",body,"report-test"))
                with self.assertRaises(HTTPException) as caught:
                    api.create_cited_report("DF-24-017",{**body,"title":"Different"},"report-test")
                self.assertEqual(caught.exception.status_code,409)
                graph.available = False
                ident = first["data"]["id"]
                export = api.export_cited_report("DF-24-017",ident,"json")
                envelope = json.loads(export.body)
                self.assertEqual(envelope["contentSha256"],content_digest(envelope["report"]))
                self.assertIn("Content-Security-Policy".lower(),api.export_cited_report("DF-24-017",ident,"html").headers)
                with api.connect() as db:
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM report_snapshots").fetchone()[0],1)
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM audit_events WHERE action='report.cited_draft_created'").fetchone()[0],1)
                    db.execute("UPDATE report_snapshots SET content_sha256='tampered'")
                with self.assertRaises(HTTPException) as caught:
                    api.read_cited_report("DF-24-017",ident)
                self.assertEqual(caught.exception.detail["code"],"REPORT_INTEGRITY_FAILED")

    def test_report_not_found_is_case_scoped(self):
        with tempfile.TemporaryDirectory(dir=api.ROOT) as temp:
            with patch.object(api,"DB_PATH",Path(temp)/"case.sqlite3"):
                api.initialize(seed_demo=True)
                with self.assertRaises(HTTPException) as caught:
                    api.read_cited_report("DF-24-017","RPT-from-another-case")
                self.assertEqual(caught.exception.status_code,404)
