"""Idempotently copy legacy SQLite agent_memory rows into case-scoped FalkorDB.

Run from the repository root. Default is a read-only plan; pass --apply to write.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.graph_store import CaseGraph

DB_PATH = Path(os.getenv("SUTRAM_DB_PATH", str(ROOT / "backend" / "data" / "sutram.sqlite3")))
VALID_STATES = {"observed", "derived", "candidate", "hypothesis", "unknown"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write graph episodes and append migration audit events")
    args = parser.parse_args()
    if not DB_PATH.is_file():
        raise SystemExit(f"SQLite database was not found: {DB_PATH}")
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM agent_memory ORDER BY case_id,created_at,id").fetchall()
        cases = {row["case_id"]: json.loads(row["snapshot_json"]) for row in db.execute("SELECT case_id,snapshot_json FROM cases")}
        uploaded_sources = {}
        for row in db.execute("SELECT case_id,artifact_id FROM artifact_files"):
            uploaded_sources.setdefault(row["case_id"], set()).add(row["artifact_id"])
    print(f"Found {len(rows)} legacy memory record(s). Mode: {'APPLY' if args.apply else 'DRY RUN'}.")
    for row in rows:
        case_id = row["case_id"]
        if case_id not in cases:
            raise SystemExit(f"Missing case snapshot for legacy record {row['id']}; no safe source allowlist exists.")
        known = {str(item.get("id")) for item in cases[case_id].get("evidence", []) if isinstance(item, dict) and item.get("id")}
        known.update(uploaded_sources.get(case_id, set()))
        try:
            requested_sources = json.loads(row["sources_json"] or "[]")
        except (TypeError, json.JSONDecodeError):
            requested_sources = []
        source_ids = sorted({str(item) for item in requested_sources if str(item) in known}) if isinstance(requested_sources, list) else []
        try:
            payload = json.loads(row["result_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            payload = {"legacyResultUnreadable": True}
        state = payload.get("state", "unknown") if isinstance(payload, dict) else "unknown"
        if state not in VALID_STATES:
            state = "unknown"
        agent_id = row["agent_id"] if isinstance(row["agent_id"], str) else "legacy-memory"
        if not agent_id or not all(ch.islower() or ch.isdigit() or ch == "-" for ch in agent_id) or not agent_id[0].isalnum() or len(agent_id) > 64:
            agent_id = "legacy-memory"
        kind = "legacy-episodic"
        migrated_payload = {"question": row["question"], "answer": row["answer"], "legacyResult": payload,
                            "migrationSource": "sqlite.agent_memory"}
        if agent_id == "case-orchestrator" and isinstance(payload, dict) and isinstance(payload.get("workstreams"), list):
            kind = "case-synthesis"
            migrated_payload = payload
            state = "derived"
        elif agent_id in {"context-narrator", "context-planner", "evidence-path-agent"}:
            agent_id = "context-planner"
            kind = "graph-question"
            migrated_payload = {"entityId": row["entity_id"], "question": row["question"], "answer": row["answer"], "result": payload}
        elif agent_id == "case-orchestrator":
            # Malformed old payloads remain isolated from the hub's typed run view.
            agent_id = "legacy-memory"
        episode_id = "EP-" + hashlib.sha256(f"legacy:{row['id']}".encode()).hexdigest()[:24]
        print(f"{case_id} {row['id']} -> {episode_id} · {agent_id} · {state} · {len(source_ids)} case-known source(s)")
        if not args.apply:
            continue
        graph = CaseGraph(case_id)
        if not graph.available:
            raise SystemExit(f"FalkorDB is unavailable for case {case_id}; safe to retry because episode IDs are stable.")
        graph.remember_episode(episode_id=episode_id, agent_id=agent_id, kind=kind,
                               summary=(row["answer"] or row["question"] or "Legacy episodic memory"),
                               evidence_state=state, source_ids=source_ids,
                               payload=migrated_payload,
                               idempotency_key=f"legacy-migration:{row['id']}", created_at=row["created_at"])
        with sqlite3.connect(DB_PATH) as db:
            stamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            exists = db.execute("SELECT 1 FROM audit_events WHERE case_id=? AND action='agent.memory_migrated' AND entity_id=? LIMIT 1", (case_id, episode_id)).fetchone()
            if not exists:
                db.execute("INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?)",
                           (str(uuid.uuid4()), case_id, "local-development-user", "agent.memory_migrated", "agent_episode",
                            episode_id, json.dumps({"legacyMemoryId": row["id"], "sourceIds": source_ids}), stamp))
            db.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
