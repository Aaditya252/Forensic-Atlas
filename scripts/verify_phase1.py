"""Live FalkorDB/API smoke checks on a disposable fictional case.

Run from the repository root. Optional --restart-container verifies persistence
after a graceful restart of the named local Docker container (all its graphs).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fastapi.testclient import TestClient
import backend.app as api
from backend.graph_store import CaseGraph


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restart-container", help="Gracefully restart this local FalkorDB Docker container after checkpointing")
    args = parser.parse_args()
    report = {"startedAt": datetime.now(timezone.utc).isoformat(), "checks": [], "status": "running"}
    output = ROOT / "output" / "phase1-verification.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    case_id = "PHASE1-" + uuid.uuid4().hex[:16]
    graph = CaseGraph(case_id)
    if not graph.available:
        raise SystemExit("FalkorDB is unavailable; live verification did not run.")
    other = None

    def check(name: str, condition: bool) -> None:
        report["checks"].append({"name": name, "passed": bool(condition)})
        print(f"{'PASS' if condition else 'FAIL'} {name}", flush=True)
        if not condition:
            raise AssertionError(name)

    try:
        demo = CaseGraph("DF-24-017")
        if demo.available:
            existing_memories = {item["id"] for item in demo.list_episodes(limit=100)}
            existing_handoffs = {item["id"] for item in demo.list_handoffs(limit=100)}
            demo_snapshot = json.loads(api.DEMO_PATH.read_text(encoding="utf-8-sig"))
            demo.upsert_demo_projection(demo_snapshot)
            node_count = len(demo.list_entities(limit=250))
            demo.upsert_demo_projection(demo_snapshot)
            check("demo reseed preserves memory and handoffs", existing_memories == {item["id"] for item in demo.list_episodes(limit=100)} and existing_handoffs == {item["id"] for item in demo.list_handoffs(limit=100)})
            check("demo reseed does not duplicate entities", len(demo.list_entities(limit=250)) == node_count)
        with tempfile.TemporaryDirectory(prefix="phase1-", dir=ROOT / "output") as temp:
            with patch.object(api, "DB_PATH", Path(temp) / "case.sqlite3"):
                api.initialize()
                snapshot = json.loads(api.DEMO_PATH.read_text(encoding="utf-8-sig"))
                snapshot["case"]["id"] = case_id
                with api.connect() as db:
                    db.execute("INSERT INTO cases VALUES(?,?,?,?)", (case_id, json.dumps(snapshot), api.now(), api.now()))
                for entity_id, label in (("SES-0942", "Session"), ("DEV-114", "Device"), ("ART-028", "Artifact")):
                    graph.graph.query("CREATE (:CaseEntity {caseId:$caseId,id:$id,label:$label,name:$id,source:'ART-028',claim:'observed'})",
                                      params={"caseId": case_id, "id": entity_id, "label": label})
                graph.graph.query("MATCH (s:CaseEntity {caseId:$caseId,id:'SES-0942'}),(d:CaseEntity {caseId:$caseId,id:'DEV-114'}) "
                                  "CREATE (s)-[:OBSERVED_ON {caseId:$caseId,state:'observed',artifactId:'ART-028'}]->(d)", params={"caseId": case_id})
                base = f"/api/v1/cases/{case_id}"
                with TestClient(api.app) as client:
                    check("workspace API", client.get(base + "/workspace").status_code == 200)
                    for page in ("evidence", "coverage", "timeline", "entities", "media", "deepfake", "review", "acquisitions", "reports", "settings", "agents"):
                        check(f"{page} page read model", client.get(base + "/pages/" + page).status_code == 200)
                    context = client.post(base + "/context/ask", headers={"Idempotency-Key": "context-phase1"},
                                          json={"entityId": "SES-0942", "question": "What evidence-linked entities connect to this record?", "depth": 2})
                    check("verified graph context", context.status_code == 200 and context.json()["data"].get("verification", {}).get("ok") is True)
                    first = client.post(base + "/agents/hub/run", headers={"Idempotency-Key": "hub-phase1"}, json={})
                    check("persistent coordinator run", first.status_code == 200)
                    run_id = first.json()["data"]["runId"]
                    repeat = client.post(base + "/agents/hub/run", headers={"Idempotency-Key": "hub-phase1"}, json={})
                    check("idempotent coordinator replay", repeat.status_code == 200 and repeat.json() == first.json())
                    handoffs = client.get(base + "/agents/handoffs").json()["data"]["items"]
                    check("four source-linked specialist handoffs", len(handoffs) == 4 and all(item["caseId"] == case_id for item in handoffs))
                    ack_path = base + "/agents/handoffs/" + handoffs[0]["id"] + "/ack"
                    ack = client.post(ack_path, headers={"Idempotency-Key": "ack-phase1"}, json={"expectedVersion": 1})
                    check("handoff acknowledgement", ack.status_code == 200 and ack.json()["data"]["version"] == 2)
                    replay = client.post(ack_path, headers={"Idempotency-Key": "ack-phase1"}, json={"expectedVersion": 1})
                    check("idempotent acknowledgement replay", replay.status_code == 200 and replay.json() == ack.json())
                    stale = client.post(ack_path, headers={"Idempotency-Key": "stale-phase1"}, json={"expectedVersion": 1})
                    check("stale acknowledgement conflict", stale.status_code == 409)
                    invalid = client.post(base + "/agents/handoffs", headers={"Idempotency-Key": "unknown-source-phase1"},
                                          json={"fromAgent": "case-orchestrator", "toAgent": "graph-context", "task": "Review", "sourceIds": ["ART-UNKNOWN"]})
                    check("reject out-of-case sources", invalid.status_code == 422)
                    other = CaseGraph(case_id + "-other")
                    check("case memory isolation", other.available and other.list_episodes() == [] and other.list_handoffs() == [])
                    with patch.object(api, "CaseGraph", lambda _: type("OfflineGraph", (), {"available": False})()):
                        offline = client.post(base + "/agents/hub/run", headers={"Idempotency-Key": "offline-phase1"}, json={})
                        check("graph outage fails closed", offline.status_code == 503)
                    with api.connect() as db:
                        check("SQLite audit without new SQLite memory", db.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0] > 0 and db.execute("SELECT COUNT(*) FROM agent_memory").fetchone()[0] == 0)
                    if args.restart_container:
                        checkpoint = subprocess.run(["docker", "exec", args.restart_container, "redis-cli", "SAVE"], check=True, capture_output=True, text=True)
                        check("graph disk checkpoint", checkpoint.stdout.strip() == "OK")
                        subprocess.run(["docker", "restart", args.restart_container], check=True, capture_output=True, text=True)
                        deadline = time.monotonic() + 40
                        while time.monotonic() < deadline:
                            if CaseGraph(case_id).available:
                                break
                            time.sleep(0.5)
                        restored = client.get(base + "/agents/hub")
                        check("memory survives database restart", restored.status_code == 200 and restored.json()["data"]["latestRun"]["runId"] == run_id)
                        restored_handoffs = client.get(base + "/agents/handoffs").json()["data"]["items"]
                        check("handoff acknowledgement survives restart", any(item["id"] == handoffs[0]["id"] and item["status"] == "acknowledged" and item["version"] == 2 for item in restored_handoffs))
                with TestClient(api.app) as restarted_api:
                    check("new API lifecycle reads persistent memory", restarted_api.get(base + "/agents/hub").json()["data"]["latestRun"]["runId"] == run_id)
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["errorType"] = type(exc).__name__
        raise
    finally:
        # Only the random graph names created by this script are removed.
        for owned in (graph, other):
            if owned is not None:
                try:
                    current = CaseGraph(owned.case_id)
                    if current.available:
                        current.graph.delete()
                except Exception:
                    report.setdefault("cleanupWarnings", []).append(owned.case_id)
        report["finishedAt"] = datetime.now(timezone.utc).isoformat()
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Report: {output}", flush=True)


if __name__ == "__main__":
    main()
