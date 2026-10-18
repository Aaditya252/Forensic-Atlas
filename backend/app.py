"""Local development API for the SUTRAM forensic workspace.

This service is deliberately loopback-only and is not an evidence-capture
service. Deployments handling real evidence need authentication, authorization,
encrypted object storage, and an independently reviewed custody workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import uuid
import sqlite3
import threading
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from .agents.context_orchestrator import run_context_orchestrator
from .agents.hybrid_hub import AGENT_ROSTER, build_case_brief
from .agents.review_triage import triage_reviews
from .agents.parser_coverage import inspect_parser_coverage
from .agents.transcript_attribution import draft_speaker_labels
from .agents.timeline_normalizer import normalize_timeline
from .agents.case_summary import generate_summary
from .agents.memory_recall import recall_episodes, episode_detail
from .local_llm import LocalLLM, ModelError
from .graph_store import CaseGraph
from .reporting import build_report, content_digest, render_html
from .media_inspection import inspect_file
from .agents.media_context import assess_media_context
from .waveform import extract_waveform, WaveformError
from .relationship_view import build_relationship_view
from .audio_screen import screen_audio

ROOT = Path(__file__).resolve().parent
DATA_ROOT = ROOT.parent / "cases" / "storage"
DB_PATH = Path(os.getenv("SUTRAM_DB_PATH", str(DATA_ROOT / "sutram.sqlite3")))
SCHEMA_PATH = ROOT / "schema.sql"
DEMO_PATH = ROOT / "demo-workspace.json"
UI_ROOT = Path(os.getenv("SUTRAM_UI_PATH", str(ROOT.parent / "ui-prototype")))
if not UI_ROOT.is_dir():
    UI_ROOT = ROOT.parent / "frontend"
MAX_BODY_BYTES = 1_000_000
MAX_UPLOAD_BYTES = 512 * 1024 * 1024
SUMMARY_RUN_LOCK = threading.Lock()
MEDIA_INSPECTION_LOCK = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def with_media_inspections(case_id: str, snapshot: dict) -> dict:
    with connect() as db:
        records = db.execute('SELECT result_json FROM artifact_inspections WHERE case_id=? ORDER BY created_at DESC LIMIT 100',(case_id,)).fetchall()
    latest, seen = [], set()
    for row in records:
        try:
            record = json.loads(row['result_json'])
        except (TypeError,ValueError):
            continue
        if not isinstance(record,dict) or record.get('caseId') != case_id or not isinstance(record.get('artifactId'),str) or record.get('artifactId') in seen:
            continue
        seen.add(record.get('artifactId'))
        latest.append(record)
        if len(latest)>=20:
            break
    return {**snapshot,'mediaInspections':latest}


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize(seed_demo: bool = False) -> None:
    with connect() as db:
        db.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        if seed_demo:
            snapshot = json.loads(DEMO_PATH.read_text(encoding="utf-8-sig"))
            stamp = now()
            db.execute(
                "INSERT OR IGNORE INTO cases(case_id,snapshot_json,created_at,updated_at) VALUES(?,?,?,?)",
                (snapshot["case"]["id"], json.dumps(snapshot), stamp, stamp),
            )


def get_case(case_id: str) -> dict[str, Any]:
    with connect() as db:
        row = db.execute("SELECT snapshot_json FROM cases WHERE case_id=?", (case_id,)).fetchone()
    if not row:
        raise HTTPException(404, detail={"code": "CASE_NOT_FOUND", "message": "This case is not present in the local workspace database."})
    snapshot = json.loads(row["snapshot_json"])
    for item in snapshot["evidence"]:
        item.setdefault("hasStoredBytes",False)
    snapshot["reviewItems"] = [item for item in snapshot["reviewItems"] if not has_decision(case_id, item["id"])]
    with connect() as db:
        uploaded = db.execute("SELECT artifact_id,original_name,media_type,source_label,byte_size,sha256,created_at FROM artifact_files WHERE case_id=? ORDER BY created_at DESC", (case_id,)).fetchall()
    with connect() as db:
        saved_inspections = db.execute('SELECT artifact_id,result_json FROM artifact_inspections WHERE case_id=? ORDER BY created_at DESC LIMIT 1000',(case_id,)).fetchall()
    audio_tracks = {}
    for record in saved_inspections:
        if record['artifact_id'] not in audio_tracks:
            inspection = json.loads(record['result_json'])
            audio_tracks[record['artifact_id']] = any(stream.get('codec_type') == 'audio' for stream in inspection.get('streams',[])) if inspection.get('status') == 'completed' else None
    for row in uploaded:
        size = int(row["byte_size"])
        size_label = f"{size / (1024 * 1024):.1f} MB" if size >= 1024 * 1024 else f"{size / 1024:.1f} KB"
        created = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        snapshot["evidence"].append({"id": row["artifact_id"], "name": row["original_name"], "type": row["media_type"], "source": row["source_label"], "date": created.strftime("%d %b · %H:%M UTC"), "size": size_label, "status": "verified", "icon": "media" if row["media_type"].lower() in {"video", "audio", "image"} else "file", "sha256": row["sha256"], "hasStoredBytes": True, "hasAudioTrack": audio_tracks.get(row["artifact_id"])})
    snapshot["overview"]["evidenceItems"] = max(int(snapshot["overview"].get("evidenceItems", 0)), 0) + len(uploaded)
    snapshot["overview"]["totalArtifacts"] = int(snapshot["overview"].get("totalArtifacts", 0)) + len(uploaded)
    snapshot["overview"]["verifiedArtifacts"] = int(snapshot["overview"].get("verifiedArtifacts", 0)) + len(uploaded)
    snapshot["overview"]["reviewQueueItems"] = len(snapshot["reviewItems"])
    snapshot["updatedAt"] = now()
    return snapshot


def has_decision(case_id: str, review_id: str) -> bool:
    with connect() as db:
        return db.execute("SELECT 1 FROM review_decisions WHERE case_id=? AND review_id=? LIMIT 1", (case_id, review_id)).fetchone() is not None


def audit(db: sqlite3.Connection, case_id: str, action: str, entity_type: str, entity_id: str, details: dict[str, Any]) -> None:
    db.execute(
        "INSERT INTO audit_events VALUES(?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), case_id, "local-development-user", action, entity_type, entity_id, json.dumps(details), now()),
    )


def decode_body(request: Request, body: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise HTTPException(400, detail={"code": "INVALID_BODY", "message": "A JSON object is required."})
    return body


def idempotent_response(db: sqlite3.Connection, case_id: str, key: str | None) -> dict[str, Any] | None:
    if not key or len(key) > 200:
        raise HTTPException(400, detail={"code": "IDEMPOTENCY_KEY_REQUIRED", "message": "Provide a valid Idempotency-Key for this write."})
    row = db.execute("SELECT response_json FROM idempotency_keys WHERE case_id=? AND key=?", (case_id, key)).fetchone()
    return json.loads(row["response_json"]) if row else None


def save_idempotency(db: sqlite3.Connection, case_id: str, key: str, response: dict[str, Any]) -> None:
    db.execute("INSERT INTO idempotency_keys VALUES(?,?,?,?)", (case_id, key, json.dumps(response), now()))


def scoped_record_id(case_id: str, key: str, prefix: str) -> str:
    """Stable graph ID makes a retried write safe across the graph/SQLite boundary."""
    digest = hashlib.sha256(f"{case_id}\0{key}".encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{digest}"


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize(seed_demo=os.getenv("SUTRAM_SEED_DEMO", "0") == "1")
    yield


app = FastAPI(title="Forensic Atlas local case API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in os.getenv("SUTRAM_CORS_ORIGINS", "http://localhost:4173,http://127.0.0.1:4173").split(",") if x.strip()],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "Authorization", "X-Request-Id", "Idempotency-Key"],
    expose_headers=["X-Request-Id"],
)


@app.middleware("http")
async def request_guard(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))[:128]
    if request.method in {"POST", "PUT", "PATCH"} and "application/json" in request.headers.get("content-type", ""):
        length = request.headers.get("content-length")
        if length and int(length) > MAX_BODY_BYTES:
            return error_response(413, "BODY_TOO_LARGE", "This local JSON endpoint accepts requests up to 1 MB.")
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(HTTPException)
async def safe_http_errors(_: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})
    return error_response(exc.status_code, "REQUEST_REJECTED", str(exc.detail))


@app.get("/health")
def health():
    db_ok = False
    try:
        with connect() as db:
            db.execute("SELECT 1")
        db_ok = True
    except sqlite3.Error:
        pass
    graph = CaseGraph("health-check")
    return {
        "service": "forensic-atlas",
        "status": "ok" if db_ok and graph.available else "degraded",
        "storage": {"sqlite": db_ok, "path": str(DB_PATH)},
        "graph": {"provider": "FalkorDB", "connected": graph.available},
        "models": {"localLLM": LocalLLM().status(), "validatedMediaDetector": False, "message": "No validated media detector is configured."},
        "environment": "local-development-only",
    }


@app.get("/api/v1/cases/{case_id}/workspace")
def workspace(case_id: str):
    return {"data": get_case(case_id)}


def page_data(case_id: str, page: str) -> dict[str, Any]:
    snapshot = get_case(case_id)
    evidence = snapshot["evidence"]
    if page == "evidence":
        columns = [("id", "Artifact ID"), ("name", "Name"), ("type", "Type"), ("source", "Source"), ("status", "Status"), ("sha256", "SHA-256")]
        rows = evidence
        metrics = [{"label": "Registered artifacts", "value": len(evidence), "unit": "items", "foot": "Local case database", "kind": "teal", "icon": "evidence"}]
        title, summary, section = "Evidence library", "Case-scoped artifact metadata.", "Artifacts"
    elif page == "coverage":
        columns = [("name", "Source class"), ("count", "Acquired / expected"), ("pct", "Coverage"), ("state", "State")]
        rows = snapshot["sourceCoverage"]
        metrics = [{"label": "Source classes", "value": len(rows), "unit": "classes", "kind": "blue", "icon": "coverage"}]
        title, summary, section = "Source coverage", "Coverage state from the seeded case plan.", "Source classes"
    elif page == "timeline":
        normalized = normalize_timeline(snapshot["events"], {str(item.get("id")) for item in evidence if item.get("id")})
        normalized_by_id = {item["eventId"]: item for item in normalized["items"]}
        rows = [{**event, "normalizedUtc": normalized_by_id.get(str(event.get("id")), {}).get("normalizedUtc"),
                 "timePrecision": normalized_by_id.get(str(event.get("id")), {}).get("precision"),
                 "offsetStatus": normalized_by_id.get(str(event.get("id")), {}).get("offsetStatus"),
                 "timeState": normalized_by_id.get(str(event.get("id")), {}).get("state")} for event in snapshot["events"]]
        columns = [("time", "Source time"), ("normalizedUtc", "Normalized UTC"), ("timePrecision", "Text precision"), ("offsetStatus", "Offset"), ("title", "Event"), ("source", "Source artifact")]
        metrics = [{"label": "Events in local view", "value": len(rows), "unit": "records", "foot": "Sample rows", "kind": "blue", "icon": "timeline"}]
        title, summary, section = "Investigation timeline", "Events retain source references; timestamps are display data.", "Events"
    elif page == "entities":
        graph = CaseGraph(case_id)
        rows = graph.list_entities() if graph.available else []
        columns = [("id", "Entity ID"), ("label", "Type"), ("name", "Name"), ("source", "Evidence source"), ("claim", "Evidence state")]
        metrics = [{"label": "Graph entities", "value": len(rows), "unit": "nodes", "foot": "FalkorDB projection", "kind": "teal", "icon": "entities"}]
        title = "Evidence relationship graph"
        summary = "FalkorDB is the source for graph entities; SQLite stores case records and the audit trail." if graph.available else "FalkorDB is the required relationship store for graph reasoning. Connect it to load this case's graph."
        section = "FalkorDB entities" if graph.available else "Graph service not connected"
        memory_rows = graph.list_episodes(limit=5, agent_id="context-planner") if graph.available else []
        agent_memory = [{"id": row["id"], "agent_id": row["agentId"], "entity_id": row.get("payload", {}).get("entityId", ""),
                         "question": row.get("payload", {}).get("question", row.get("summary", "")),
                         "answer": row.get("payload", {}).get("answer", ""), "sources": row.get("sourceIds", []),
                         "created_at": row.get("createdAt")} for row in memory_rows]
    elif page in {"media", "deepfake"}:
        rows = [item for item in evidence if any(word in item.get("type", "").lower() for word in ("video", "audio", "image", "media"))]
        columns = [("id", "Artifact ID"), ("name", "Media"), ("type", "Modality"), ("source", "Source"), ("status", "Integrity state")]
        metrics = [{"label": "Media artifacts", "value": len(rows), "unit": "items", "foot": "Detector is not configured", "kind": "blue", "icon": "media"}]
        title, summary, section = ("Deepfake analysis", "No detector scores are fabricated; model runs remain blocked until a validated provider is configured.", "Media evidence") if page == "deepfake" else ("Media analysis", "Metadata and screening workflow status.", "Media artifacts")
        if page == "deepfake":
            with connect() as db:
                runs = db.execute("SELECT id,artifact_id,status,created_at FROM media_runs WHERE case_id=? ORDER BY created_at DESC", (case_id,)).fetchall()
            rows = [dict(row) for row in runs] or rows
            columns = [("id", "Run / artifact ID"), ("artifact_id", "Artifact"), ("status", "Run state"), ("created_at", "Created")]
    elif page == "review":
        rows = snapshot["reviewItems"]
        columns = [("id", "Review ID"), ("type", "Type"), ("title", "Claim"), ("priority", "Priority"), ("evidence", "Evidence reference")]
        metrics = [{"label": "Open reviews", "value": len(rows), "unit": "items", "kind": "amber", "icon": "review"}]
        title, summary, section = "AI review queue", "Examiner decisions are appended to an audit table.", "Open review items"
    elif page in {"acquisitions", "reports"}:
        kind = "acquisition" if page == "acquisitions" else "report"
        with connect() as db:
            items = db.execute("SELECT id,status,payload_json,created_at FROM case_records WHERE case_id=? AND kind=? ORDER BY created_at DESC", (case_id, kind)).fetchall()
        rows = [{"id": x["id"], "status": x["status"], **json.loads(x["payload_json"]), "created_at": x["created_at"]} for x in items]
        columns = [("id", "ID"), ("status", "State"), ("created_at", "Created")]
        metrics = [{"label": "Saved requests", "value": len(rows), "unit": "records", "foot": "No external connector is contacted", "kind": "teal", "icon": "file"}]
        title, summary, section = ("Acquisition jobs", "Requests persist locally; no cloud source connector is configured.", "Acquisition requests") if page == "acquisitions" else ("Reports & exports", "Draft metadata persists locally; rendering is not configured.", "Report drafts")
        if page == "reports":
            with connect() as db:
                saved = db.execute("SELECT id,title,summary_episode_id,content_sha256,created_at FROM report_snapshots WHERE case_id=? ORDER BY created_at DESC LIMIT 100", (case_id,)).fetchall()
            rows = [{**dict(row), "status": "unreviewed_draft", "renderable": True} for row in saved] + rows
            columns = [("id", "ID"), ("title", "Title"), ("status", "State"), ("created_at", "Created")]
            summary = "Saved cited report snapshots and legacy metadata requests. Every generated report remains an unreviewed draft."
            metrics = [{"label": "Cited report snapshots", "value": len(saved), "unit": "drafts", "foot": "Immutable snapshots · latest 100", "kind": "teal", "icon": "reports"}]
    elif page == "settings":
        rows = [{"component": "Case database", "provider": "SQLite local development", "status": "connected"}, {"component": "Relationship graph", "provider": "FalkorDB", "status": "connected" if CaseGraph(case_id).available else "not connected"}, {"component": "Media detector", "provider": "validated model plugin", "status": "not configured"}]
        columns = [("component", "Component"), ("provider", "Provider"), ("status", "Status")]
        metrics = []
        title, summary, section = "Workspace settings", "Local service state; production identity controls are not configured.", "Service providers"
    elif page == "agents":
        rows = AGENT_ROSTER
        columns = [("name", "Specialist agent"), ("domain", "Domain"), ("mode", "Method"), ("status", "Availability"), ("description", "Role")]
        metrics = [{"label": "Specialist agents", "value": len(rows), "unit": "agents", "foot": "Case-scoped workflow", "kind": "teal", "icon": "entities"}]
        title, summary, section = "Hybrid agent hub", "Coordinated, source-grounded agents for graphs, multimedia, and forensic research.", "Agent roster"
    else:
        raise HTTPException(404, detail={"code": "PAGE_NOT_FOUND", "message": "The requested case view does not exist."})
    result = {"schemaVersion": 1, "title": title, "summary": summary, "sectionTitle": section, "sectionDescription": summary, "metrics": metrics, "columns": [{"key": key, "label": label} for key, label in columns], "rows": rows, "updatedAt": now()}
    if page == "media":
        with connect() as db:
            uploaded_media = db.execute("SELECT artifact_id,original_name,media_type FROM artifact_files WHERE case_id=? AND media_type IN ('Audio','Video','Image') ORDER BY created_at DESC LIMIT 100",(case_id,)).fetchall()
        result['storedArtifacts'] = [dict(row) for row in uploaded_media]
    if page == "entities":
        result["agentMemory"] = agent_memory
        with connect() as db:
            inspections = [json.loads(row['result_json']) for row in db.execute('SELECT result_json FROM artifact_inspections WHERE case_id=? ORDER BY created_at DESC LIMIT 20',(case_id,))]
            reports = [dict(row) for row in db.execute('SELECT id,title,summary_episode_id,content_sha256 FROM report_snapshots WHERE case_id=? ORDER BY created_at DESC LIMIT 20',(case_id,))]
        result['relationshipGraph'] = build_relationship_view(snapshot, rows,
            graph.list_relationships() if graph.available else [], inspections,
            graph.list_episodes(limit=20) if graph.available else [], reports, graph.available)
    return result


@app.get("/api/v1/cases/{case_id}/pages/{page}")
def read_page(case_id: str, page: str):
    return {"data": page_data(case_id, page)}


@app.get("/api/v1/cases/{case_id}/agents/hub")
def read_agent_hub(case_id: str):
    get_case(case_id)
    graph = CaseGraph(case_id)
    if not graph.available:
        raise HTTPException(503, detail={"code": "FALKORDB_UNAVAILABLE", "message": "The agent hub requires FalkorDB for shared, persistent case memory."})
    try:
        episodes = graph.list_episodes(limit=100, agent_id="case-orchestrator")
        recent_memory = graph.list_episodes(limit=6)
        recent_handoffs = graph.list_handoffs(limit=6)
        summaries = graph.list_episodes(limit=1, agent_id="case-summary")
    except Exception:
        raise HTTPException(503, detail={"code": "AGENT_MEMORY_UNAVAILABLE", "message": "FalkorDB could not read this case's agent memory."})
    latest = episodes[0].get("payload") if episodes else None
    summary_provider = LocalLLM().status()
    return {"data": {"roster": AGENT_ROSTER, "latestRun": latest, "memory": recent_memory, "handoffs": recent_handoffs,
                      "latestSummary": summaries[0].get("payload") if summaries else None, "summaryProvider": summary_provider,
                      "provider": {"llm": summary_provider["status"], "mediaDetector": "not-configured", "graph": "available"}}}


@app.get("/api/v1/cases/{case_id}/summary")
def read_case_summary(case_id: str):
    get_case(case_id)
    graph = CaseGraph(case_id)
    if not graph.available:
        raise HTTPException(503, detail={"code": "FALKORDB_UNAVAILABLE", "message": "The cited summary requires the case memory graph."})
    try:
        rows = graph.list_episodes(limit=1, agent_id="case-summary")
    except Exception:
        raise HTTPException(503, detail={"code": "AGENT_MEMORY_UNAVAILABLE", "message": "The case summary could not be read from FalkorDB."})
    return {"data": {"latestSummary": rows[0]["payload"] if rows else None, "provider": LocalLLM().status()}}


@app.post("/api/v1/cases/{case_id}/summary")
def create_case_summary(case_id: str, body: dict[str, Any], idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    snapshot = with_media_inspections(case_id,get_case(case_id))
    if set(body) - {"entityId"} or (body.get("entityId") is not None and (not isinstance(body["entityId"], str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", body["entityId"]))):
        raise HTTPException(422, detail={"code": "INVALID_SUMMARY_REQUEST", "message": "Provide an optional safe entityId; other fields are unsupported."})
    if not idempotency_key or len(idempotency_key) > 200:
        raise HTTPException(400, detail={"code": "IDEMPOTENCY_KEY_REQUIRED", "message": "Provide a valid Idempotency-Key for this summary."})
    request_digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    operation_key = "case-summary:" + hashlib.sha256(idempotency_key.encode()).hexdigest()
    with connect() as db:
        cached = idempotent_response(db, case_id, operation_key)
        if cached:
            if cached.get("data", {}).get("requestDigest") != request_digest:
                raise HTTPException(409, detail={"code": "IDEMPOTENCY_CONFLICT", "message": "This summary key belongs to different request parameters."})
            return cached
    if not SUMMARY_RUN_LOCK.acquire(blocking=False):
        raise HTTPException(429, detail={"code": "SUMMARY_BUSY", "message": "A local summary is already running. Wait for it to finish before retrying."})
    try:
        graph = CaseGraph(case_id)
        if not graph.available:
            raise HTTPException(503, detail={"code": "FALKORDB_UNAVAILABLE", "message": "The summary requires source-linked graph context and persistent case memory."})
        model = LocalLLM()
        # Recover a graph write that succeeded before the SQLite transaction did.
        summary_id = scoped_record_id(case_id, operation_key, "SUM")
        episodes = graph.list_episodes(limit=100, agent_id="case-summary")
        saved = next((row["payload"] for row in episodes if row.get("payload", {}).get("summaryId") == summary_id), None)
        if saved:
            if saved.get("requestDigest") != request_digest:
                raise HTTPException(409, detail={"code": "IDEMPOTENCY_CONFLICT", "message": "This summary key belongs to different parameters."})
            result = saved
        else:
            if not model.status().get("ready"):
                raise ModelError("LOCAL_LLM_UNAVAILABLE", "The local model is not ready. Start the Phase 2 model service to generate a cited draft.")
            result = generate_summary(snapshot, graph, model, body.get("entityId"))
            result.update(summaryId=summary_id, caseId=case_id, createdAt=now(), requestDigest=request_digest)
            graph.remember_episode(episode_id=scoped_record_id(case_id, operation_key, "EP"), agent_id="case-summary",
                                   kind="case-summary", summary="Cited extractive summary draft", evidence_state=result["state"],
                                   source_ids=result["sources"], payload=result, idempotency_key=operation_key, created_at=result["createdAt"])
        response = {"data": result}
        with connect() as db:
            audit(db, case_id, "agent.case_summary_created", "case_summary", result["summaryId"],
                  {"model": result["model"], "sources": result["sources"], "contextDigest": result["contextDigest"],
                   "verification": result["verification"], "method": result["method"]})
            save_idempotency(db, case_id, operation_key, response)
        return response
    except ModelError as exc:
        with connect() as db:
            audit(db, case_id, "agent.case_summary_blocked", "case", case_id, {"code": exc.code})
        status = 422 if exc.code in {"UNKNOWN_SUMMARY_ENTITY", "NO_VERIFIED_SUMMARY_CONTEXT", "SUMMARY_VERIFICATION_FAILED"} else 503
        raise HTTPException(status, detail={"code": exc.code, "message": str(exc)})
    except HTTPException:
        raise
    except Exception:
        with connect() as db:
            audit(db, case_id, "agent.case_summary_failed", "case", case_id, {"code": "SUMMARY_FAILED"})
        raise HTTPException(503, detail={"code": "SUMMARY_FAILED", "message": "The cited summary could not be completed and persisted. Check the local model and graph services."}) from None
    finally:
        SUMMARY_RUN_LOCK.release()


@app.post("/api/v1/cases/{case_id}/agents/hub/run")
def run_agent_hub(case_id: str, body: dict[str, Any], idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    snapshot = with_media_inspections(case_id,get_case(case_id))
    with connect() as db:
        cached = idempotent_response(db, case_id, idempotency_key)
        if cached:
            return cached
    graph = CaseGraph(case_id)
    if not graph.available:
        raise HTTPException(503, detail={"code": "FALKORDB_UNAVAILABLE", "message": "FalkorDB is required to run and persist a coordinated case workflow."})
    graph_entities: list[dict[str, Any]] = []
    graph_ready = graph.available
    if graph.available:
        try:
            graph_entities = graph.list_entities(250)
        except Exception:
            graph_ready = False
            graph_entities = []
    result = build_case_brief(snapshot, graph_available=graph_ready, graph_entities=graph_entities, detector_configured=False)
    media_context = assess_media_context(snapshot)
    result['mediaInspectionContext'] = media_context
    result['workstreams'].append({'agentId':'media-metadata','name':'Saved media inspection context','state':media_context['state'],
        'summary':media_context['summary'],'sources':media_context['sourceIds'],
        'impact':'Saved container and byte-integrity observations guide examination; they do not establish authenticity.',
        'nextStep':next((item['nextStep'] for item in media_context['items'] if item.get('integrityMatch') is False),
                        'Inspect uploaded media on the Media analysis page, and review historical timestamps before reuse.')})
    result["reviewTriage"] = triage_reviews(snapshot)
    parser_result = inspect_parser_coverage(snapshot)
    transcript_result = draft_speaker_labels(snapshot)
    result["parserCoverage"] = parser_result
    result["transcriptAttribution"] = transcript_result
    parser_sources = sorted({source for item in parser_result.get("items", []) for source in item.get("sourceIds", []) if source})
    transcript_sources = transcript_result.get("sourceIds", [])
    result["workstreams"].extend([
        {"agentId": "parser-coverage", "name": "Parser coverage audit", "state": parser_result.get("state", "unknown"),
         "summary": parser_result.get("gap") or f"{len(parser_result.get('items', []))} parser manifest row(s) evaluated.",
         "sources": parser_sources, "impact": "Without parsed-versus-referenced counters, downstream comparisons may have unresolved source gaps.",
         "nextStep": "Attach a versioned parser manifest with source IDs and parsed/reference counts."},
        {"agentId": "transcript-attribution", "name": "Transcript speaker-label review", "state": transcript_result.get("state", "unknown"),
         "summary": transcript_result.get("gap") or f"{len(transcript_result.get('speakerLabels', []))} supplied speaker label(s) are ready for review.",
         "sources": transcript_sources, "impact": "A diarization label can guide segment review but does not identify a person or establish who acted.",
         "nextStep": transcript_result.get("examinerNextStep", "Compare source segments manually.")},
    ])
    result["runId"] = scoped_record_id(case_id, idempotency_key, "AGENT")
    result["createdAt"] = now()
    result["caseId"] = case_id
    response = {"data": result}
    source_ids = sorted({source for item in result["workstreams"] for source in item.get("sources", [])})
    try:
        graph.remember_episode(episode_id=scoped_record_id(case_id, idempotency_key, "EP"), agent_id="case-orchestrator",
                               kind="case-synthesis", summary=result["headline"], evidence_state="derived",
                               source_ids=source_ids, payload=result, idempotency_key=idempotency_key,
                               created_at=result["createdAt"])
        created_handoffs = []
        for workstream in result["workstreams"]:
            agent_id = workstream.get("agentId")
            if agent_id not in {"integrity-coverage", "timeline-correlation", "graph-context", "impact-assessment"}:
                continue
            handoff_state = workstream.get("state")
            if handoff_state not in {"candidate", "hypothesis", "unknown", "derived"}:
                handoff_state = "derived"
            handoff = graph.create_handoff(
                handoff_id=scoped_record_id(case_id, f"{idempotency_key}:{agent_id}", "HO"),
                from_agent="case-orchestrator", to_agent=agent_id,
                task=str(workstream.get("nextStep") or "Review this workstream")[:500], state=handoff_state,
                source_ids=workstream.get("sources", []),
                context={"runId": result["runId"], "summary": workstream.get("summary", ""),
                         "impact": workstream.get("impact", ""), "alternatives": workstream.get("alternatives", [])},
                idempotency_key=f"{idempotency_key}:{agent_id}", run_id=result["runId"], created_at=result["createdAt"])
            created_handoffs.append(handoff)
    except Exception:
        raise HTTPException(503, detail={"code": "AGENT_MEMORY_WRITE_FAILED", "message": "The workflow could not persist its case-scoped memory; no successful run was recorded."})
    with connect() as db:
        audit(db, case_id, "agent.hybrid_hub_run", "case", case_id, {"runId": result["runId"], "sourceCount": len(source_ids), "agentCount": len(result["workstreams"]), "memory": "FalkorDB", "llm": "not-invoked", "detector": "not-configured"})
        for handoff in created_handoffs:
            audit(db, case_id, "agent.handoff_created", "agent_handoff", handoff["id"], {"fromAgent": handoff["fromAgent"], "toAgent": handoff["toAgent"], "state": handoff["state"], "sourceIds": handoff["sourceIds"], "runId": result["runId"]})
        save_idempotency(db, case_id, idempotency_key, response)
    return response


@app.get("/api/v1/cases/{case_id}/agents/review-triage")
def read_review_triage(case_id: str):
    snapshot = get_case(case_id)
    return {"data": triage_reviews(snapshot)}


@app.get("/api/v1/cases/{case_id}/agents/timeline-normalizer")
def read_timeline_normalization(case_id: str):
    snapshot = get_case(case_id)
    known_sources = {str(item.get("id")) for item in snapshot.get("evidence", []) if item.get("id")}
    return {"data": normalize_timeline(snapshot.get("events", []), known_sources)}


@app.get("/api/v1/cases/{case_id}/agents/parser-coverage")
def read_parser_coverage(case_id: str):
    return {"data": inspect_parser_coverage(get_case(case_id))}


@app.get("/api/v1/cases/{case_id}/agents/transcript-attribution")
def read_transcript_attribution(case_id: str):
    return {"data": draft_speaker_labels(get_case(case_id))}


@app.get("/api/v1/cases/{case_id}/agents/memory")
def read_agent_memory(case_id: str, limit: int = Query(default=20, ge=1, le=100), agent_id: str | None = Query(default=None, alias="agentId")):
    get_case(case_id)
    graph = CaseGraph(case_id)
    if not graph.available:
        raise HTTPException(503, detail={"code": "FALKORDB_UNAVAILABLE", "message": "FalkorDB is required to read shared agent memory."})
    try:
        return {"data": {"items": graph.list_episodes(limit=limit, agent_id=agent_id)}}
    except ValueError as exc:
        raise HTTPException(422, detail={"code": "INVALID_AGENT_ID", "message": str(exc)})
    except Exception:
        raise HTTPException(503, detail={"code": "AGENT_MEMORY_UNAVAILABLE", "message": "FalkorDB could not read this case's agent memory."})


@app.get("/api/v1/cases/{case_id}/agents/recall")
def recall_case_memory(case_id: str, q: str = Query(default="", max_length=160),
                       agent_id: str | None = Query(default=None, alias="agentId", max_length=64),
                       source_id: str | None = Query(default=None, alias="sourceId", max_length=36),
                       limit: int = Query(default=10, ge=1, le=20)):
    snapshot = get_case(case_id)
    known = {str(row["id"]) for row in snapshot["evidence"]}
    graph = CaseGraph(case_id)
    if not graph.available:
        raise HTTPException(503, detail={"code": "FALKORDB_UNAVAILABLE", "message": "Connect FalkorDB to search saved case memory."})
    try:
        return {"data": recall_episodes(graph.list_episodes(limit=100, agent_id=agent_id), case_id=case_id,
                                        known_sources=known, query=q, source_id=source_id, limit=limit)}
    except ValueError as exc:
        raise HTTPException(422, detail={"code": "INVALID_MEMORY_SEARCH", "message": str(exc)})
    except Exception:
        raise HTTPException(503, detail={"code": "MEMORY_RECALL_UNAVAILABLE", "message": "Saved case memory could not be searched."})


@app.get("/api/v1/cases/{case_id}/agents/recall/{episode_id}")
def read_recalled_episode(case_id: str, episode_id: str):
    snapshot = get_case(case_id)
    known = {str(row["id"]) for row in snapshot["evidence"]}
    graph = CaseGraph(case_id)
    if not graph.available:
        raise HTTPException(503, detail={"code": "FALKORDB_UNAVAILABLE", "message": "Connect FalkorDB to inspect saved case memory."})
    try:
        row = graph.get_episode(episode_id)
        if row is None:
            raise HTTPException(404, detail={"code": "EPISODE_NOT_FOUND", "message": "This episode is not present in the selected case."})
        return {"data": episode_detail(row, known)}
    except ValueError as exc:
        raise HTTPException(422, detail={"code": "INVALID_MEMORY_EPISODE", "message": str(exc)})
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, detail={"code": "MEMORY_RECALL_UNAVAILABLE", "message": "The saved episode could not be read."})


@app.get("/api/v1/cases/{case_id}/agents/handoffs")
def read_agent_handoffs(case_id: str, limit: int = Query(default=20, ge=1, le=100)):
    get_case(case_id)
    graph = CaseGraph(case_id)
    if not graph.available:
        raise HTTPException(503, detail={"code": "FALKORDB_UNAVAILABLE", "message": "FalkorDB is required to read shared agent handoffs."})
    try:
        return {"data": {"items": graph.list_handoffs(limit=limit)}}
    except Exception:
        raise HTTPException(503, detail={"code": "AGENT_HANDOFF_UNAVAILABLE", "message": "FalkorDB could not read this case's handoffs."})


@app.post("/api/v1/cases/{case_id}/agents/handoffs")
def create_agent_handoff(case_id: str, body: dict[str, Any], idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    snapshot = get_case(case_id)
    with connect() as db:
        cached = idempotent_response(db, case_id, idempotency_key)
        if cached:
            return cached
    from_agent, to_agent = body.get("fromAgent"), body.get("toAgent")
    task, state = body.get("task"), body.get("state", "candidate")
    source_ids, context = body.get("sourceIds", []), body.get("context", {})
    if not isinstance(from_agent, str) or not isinstance(to_agent, str) or not isinstance(task, str) or not task.strip():
        raise HTTPException(422, detail={"code": "INVALID_HANDOFF", "message": "fromAgent, toAgent, and a non-empty task are required."})
    allowed_agents = {str(item.get("id")) for item in AGENT_ROSTER}
    if from_agent not in allowed_agents or to_agent not in allowed_agents:
        raise HTTPException(422, detail={"code": "UNKNOWN_HANDOFF_AGENT", "message": "Handoff agents must be present in the case agent registry."})
    if not isinstance(source_ids, list) or len(source_ids) > 100 or not isinstance(context, dict):
        raise HTTPException(422, detail={"code": "INVALID_HANDOFF", "message": "Handoff sources must be a list of at most 100 IDs and context must be an object."})
    known_sources = {str(item.get("id")) for item in snapshot.get("evidence", []) if item.get("id")}
    if any(source not in known_sources for source in source_ids):
        raise HTTPException(422, detail={"code": "UNKNOWN_HANDOFF_SOURCE", "message": "Every handoff source must belong to the selected case."})
    graph = CaseGraph(case_id)
    if not graph.available:
        raise HTTPException(503, detail={"code": "FALKORDB_UNAVAILABLE", "message": "The handoff could not be accepted because FalkorDB is unavailable."})
    try:
        handoff = graph.create_handoff(handoff_id=scoped_record_id(case_id, idempotency_key, "HO"), from_agent=from_agent,
                                       to_agent=to_agent, task=task.strip(), state=state, source_ids=source_ids,
                                       context=context, idempotency_key=idempotency_key)
    except ValueError as exc:
        raise HTTPException(422, detail={"code": "INVALID_HANDOFF", "message": str(exc)})
    except Exception:
        raise HTTPException(503, detail={"code": "HANDOFF_WRITE_FAILED", "message": "FalkorDB could not persist this handoff."})
    response = {"data": handoff}
    with connect() as db:
        audit(db, case_id, "agent.handoff_created", "agent_handoff", handoff["id"], {"fromAgent": from_agent, "toAgent": to_agent, "state": state, "sourceIds": handoff["sourceIds"]})
        save_idempotency(db, case_id, idempotency_key, response)
    return response


@app.post("/api/v1/cases/{case_id}/agents/handoffs/{handoff_id}/ack")
def acknowledge_agent_handoff(case_id: str, handoff_id: str, body: dict[str, Any], idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    get_case(case_id)
    expected_version = body.get("expectedVersion")
    if set(body) != {"expectedVersion"} or not isinstance(expected_version, int) or isinstance(expected_version, bool) or expected_version < 1:
        raise HTTPException(422, detail={"code": "INVALID_HANDOFF_VERSION", "message": "Provide only the handoff version you inspected."})
    if not re.fullmatch(r"HO-[a-f0-9]{24}", handoff_id):
        raise HTTPException(422, detail={"code": "INVALID_HANDOFF", "message": "Provide a valid handoff ID."})
    if not idempotency_key or len(idempotency_key) > 200:
        raise HTTPException(400, detail={"code": "IDEMPOTENCY_KEY_REQUIRED", "message": "Provide a valid Idempotency-Key for this write."})
    operation_key = "handoff-ack:" + hashlib.sha256(idempotency_key.encode()).hexdigest()
    request_digest = hashlib.sha256(json.dumps({"handoffId": handoff_id, **body}, sort_keys=True).encode()).hexdigest()
    with connect() as db:
        cached = idempotent_response(db, case_id, operation_key)
        if cached:
            if cached.get("requestDigest") != request_digest:
                raise HTTPException(409, detail={"code": "IDEMPOTENCY_CONFLICT", "message": "This acknowledgement key belongs to another handoff or version."})
            return cached
    graph = CaseGraph(case_id)
    if not graph.available:
        raise HTTPException(503, detail={"code": "FALKORDB_UNAVAILABLE", "message": "FalkorDB is required to acknowledge this handoff."})
    try:
        acknowledged = graph.acknowledge_handoff(handoff_id, expected_version, operation_key + ":" + request_digest)
    except ValueError as exc:
        raise HTTPException(422, detail={"code": "INVALID_HANDOFF", "message": str(exc)})
    except Exception:
        raise HTTPException(503, detail={"code": "HANDOFF_WRITE_FAILED", "message": "FalkorDB could not update this handoff."})
    if acknowledged is None:
        raise HTTPException(409, detail={"code": "HANDOFF_VERSION_CONFLICT", "message": "The handoff is missing, already acknowledged, or has changed. Refresh its current state."})
    response = {"data": acknowledged, "requestDigest": request_digest}
    with connect() as db:
        # Serialize the local audit/cache commit for concurrent replays of one key.
        db.execute("BEGIN IMMEDIATE")
        cached = idempotent_response(db, case_id, operation_key)
        if cached:
            if cached.get("requestDigest") != request_digest:
                raise HTTPException(409, detail={"code": "IDEMPOTENCY_CONFLICT", "message": "This acknowledgement key belongs to another handoff or version."})
            return cached
        audit(db, case_id, "agent.handoff_acknowledged", "agent_handoff", handoff_id, acknowledged)
        save_idempotency(db, case_id, operation_key, response)
    return response


@app.get("/api/v1/cases/{case_id}/search")
def search(case_id: str, q: str = Query(default="", max_length=120), limit: int = Query(default=8, ge=1, le=25)):
    snapshot = get_case(case_id)
    needle = q.casefold().strip()
    if not needle:
        return {"data": {"items": []}}
    records = []
    for item in snapshot["evidence"]:
        records.append({"id": item["id"], "label": item["name"], "detail": f"{item['id']} · {item['type']}", "route": "evidence"})
    for item in snapshot["reviewItems"]:
        records.append({"id": item["id"], "label": item["title"], "detail": f"{item['id']} · {item['type']}", "route": "review"})
    for item in snapshot["events"]:
        records.append({"id": item["id"], "label": item["title"], "detail": f"{item['id']} · {item['source']}", "route": "timeline"})
    return {"data": {"items": [item for item in records if needle in f"{item['label']} {item['detail']}".casefold()][:limit]}}


@app.get("/api/v1/cases/{case_id}/media-runs")
def list_media_runs(case_id: str, profile: str = "multimodal-screening", limit: int = Query(default=50, ge=1, le=100)):
    get_case(case_id)
    with connect() as db:
        rows = db.execute("SELECT * FROM media_runs WHERE case_id=? ORDER BY created_at DESC LIMIT ?", (case_id, limit)).fetchall()
    items = []
    for row in rows:
        request_data, result = json.loads(row["request_json"]), json.loads(row["result_json"])
        items.append({"id": row["id"], "artifactId": row["artifact_id"], "status": row["status"], "signals": result.get("signals", []), **{k: v for k, v in result.items() if k != "signals"}})
    return {"data": {"items": items}}


@app.post("/api/v1/cases/{case_id}/artifacts")
async def upload_artifact(
    case_id: str,
    file: UploadFile = File(...),
    media_type: str = Form(...),
    source_label: str = Form(...),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    get_case(case_id)
    with connect() as db:
        cached = idempotent_response(db, case_id, idempotency_key)
        if cached:
            return cached
    if media_type not in {"Video", "Audio", "Image", "Document", "Disk image", "Log / export", "Other"}:
        raise HTTPException(422, detail={"code": "INVALID_ARTIFACT_TYPE", "message": "Choose a supported artifact type."})
    original_name = Path(file.filename or "").name.strip()
    if not original_name or original_name in {".", ".."} or len(original_name) > 255:
        raise HTTPException(422, detail={"code": "INVALID_FILENAME", "message": "The uploaded file needs a safe filename up to 255 characters."})
    source_label = source_label.strip()[:250]
    if not source_label:
        raise HTTPException(422, detail={"code": "SOURCE_REQUIRED", "message": "Provide a source or intake note."})
    ident = f"ART-{uuid.uuid4().hex[:8].upper()}"
    suffix = Path(original_name).suffix[:20]
    artifact_dir = DATA_ROOT / "evidence" / hashlib.sha256(case_id.encode("utf-8")).hexdigest()[:20]
    artifact_dir.mkdir(parents=True, exist_ok=True)
    destination = artifact_dir / f"{ident}{suffix}"
    temp_path = artifact_dir / f".{ident}.{uuid.uuid4().hex}.part"
    digest, byte_size = hashlib.sha256(), 0
    registered = False
    try:
        with temp_path.open("xb") as out:
            while chunk := await file.read(1024 * 1024):
                byte_size += len(chunk)
                if byte_size > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, detail={"code": "UPLOAD_TOO_LARGE", "message": "Local development uploads are limited to 512 MB."})
                digest.update(chunk)
                out.write(chunk)
        if byte_size == 0:
            raise HTTPException(422, detail={"code": "EMPTY_UPLOAD", "message": "The uploaded file is empty."})
        os.replace(temp_path, destination)
        stamp, sha256 = now(), digest.hexdigest()
        with connect() as db:
            db.execute("INSERT INTO artifact_files VALUES(?,?,?,?,?,?,?,?,?)", (ident, case_id, original_name, media_type, source_label, byte_size, sha256, str(destination), stamp))
            audit(db, case_id, "artifact.bytes_registered", "artifact", ident, {"name": original_name, "mediaType": media_type, "byteSize": byte_size, "sha256": sha256, "sourceLabel": source_label})
            response = {"data": {"id": ident, "message": "File stored locally and SHA-256 digest recorded. This does not certify source authenticity or chain of custody.", "sha256": sha256, "size": byte_size, "status": "digest_recorded"}}
            save_idempotency(db, case_id, idempotency_key, response)
        registered = True
        return response
    except Exception:
        temp_path.unlink(missing_ok=True)
        if not registered:
            destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


@app.get("/api/v1/cases/{case_id}/artifacts/{artifact_id}/inspection")
def read_artifact_inspection(case_id: str, artifact_id: str):
    get_case(case_id)
    with connect() as db:
        artifact = db.execute("SELECT artifact_id FROM artifact_files WHERE case_id=? AND artifact_id=?", (case_id,artifact_id)).fetchone()
        if artifact is None:
            raise HTTPException(404, detail={"code":"ARTIFACT_BYTES_NOT_FOUND","message":"Upload the original bytes before inspecting this artifact."})
        row = db.execute("SELECT result_json FROM artifact_inspections WHERE case_id=? AND artifact_id=? ORDER BY created_at DESC LIMIT 1",(case_id,artifact_id)).fetchone()
    return {"data":json.loads(row['result_json']) if row else None}


@app.post("/api/v1/cases/{case_id}/artifacts/{artifact_id}/inspection")
def create_artifact_inspection(case_id: str, artifact_id: str, body: dict[str, Any], idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    get_case(case_id)
    if body:
        raise HTTPException(422,detail={"code":"INVALID_INSPECTION_REQUEST","message":"Provide an empty object; parser arguments and paths are fixed by the service."})
    if not idempotency_key or len(idempotency_key)>200:
        raise HTTPException(400,detail={"code":"IDEMPOTENCY_KEY_REQUIRED","message":"Provide an Idempotency-Key for this inspection."})
    operation_key = 'media-inspection:'+hashlib.sha256(idempotency_key.encode()).hexdigest()
    with connect() as db:
        cached = idempotent_response(db,case_id,operation_key)
        if cached:
            if cached['data']['artifactId'] != artifact_id:
                raise HTTPException(409,detail={"code":"IDEMPOTENCY_CONFLICT","message":"This inspection key belongs to another artifact."})
            return cached
        row = db.execute("SELECT stored_path,sha256,media_type FROM artifact_files WHERE case_id=? AND artifact_id=?",(case_id,artifact_id)).fetchone()
    if row is None:
        raise HTTPException(404,detail={"code":"ARTIFACT_BYTES_NOT_FOUND","message":"Upload the original bytes before inspecting this artifact."})
    if row['media_type'] not in {'Audio','Video','Image'}:
        raise HTTPException(422,detail={"code":"UNSUPPORTED_MEDIA","message":"Choose uploaded audio, video, or image evidence."})
    if not MEDIA_INSPECTION_LOCK.acquire(blocking=False):
        raise HTTPException(429,detail={"code":"MEDIA_INSPECTION_BUSY","message":"Another metadata inspection is running. Retry after it finishes."})
    try:
        result = inspect_file(Path(row['stored_path']),row['sha256'],allowed_root=DATA_ROOT/'evidence'/hashlib.sha256(case_id.encode()).hexdigest()[:20],output_dir=ROOT.parent/'output')
    except ValueError as exc:
        raise HTTPException(422,detail={"code":"MEDIA_BYTES_UNAVAILABLE","message":str(exc)})
    finally:
        MEDIA_INSPECTION_LOCK.release()
    result.update(id=scoped_record_id(case_id,operation_key,'INS'),caseId=case_id,artifactId=artifact_id,createdAt=now(),sourceIds=[artifact_id])
    response = {'data':result}
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        cached = idempotent_response(db,case_id,operation_key)
        if cached:
            if cached['data']['artifactId'] != artifact_id:
                raise HTTPException(409,detail={"code":"IDEMPOTENCY_CONFLICT","message":"This inspection key belongs to another artifact."})
            return cached
        db.execute('INSERT INTO artifact_inspections VALUES(?,?,?,?,?)',(result['id'],case_id,artifact_id,json.dumps(result),result['createdAt']))
        audit(db,case_id,'media.metadata_inspected','artifact',artifact_id,{'inspectionId':result['id'],'status':result['status'],'sha256':result['sha256'],'integrityMatch':result['integrityMatch']})
        save_idempotency(db,case_id,operation_key,response)
    return response


@app.get("/api/v1/cases/{case_id}/artifacts/{artifact_id}/waveform")
def read_audio_waveform(case_id: str, artifact_id: str):
    get_case(case_id)
    with connect() as db:
        row=db.execute('SELECT stored_path,sha256,media_type FROM artifact_files WHERE case_id=? AND artifact_id=?',(case_id,artifact_id)).fetchone()
    if row is None:
        raise HTTPException(404,detail={'code':'ARTIFACT_BYTES_NOT_FOUND','message':'Upload audio bytes before opening a waveform.'})
    if row['media_type']!='Audio':
        raise HTTPException(422,detail={'code':'UNSUPPORTED_WAVEFORM','message':'Choose uploaded PCM WAV audio for this waveform slice.'})
    if not MEDIA_INSPECTION_LOCK.acquire(blocking=False):
        raise HTTPException(429,detail={'code':'MEDIA_INSPECTION_BUSY','message':'A media operation is running. Retry after it finishes.'})
    try:
        result=extract_waveform(Path(row['stored_path']),row['sha256'],DATA_ROOT/'evidence'/hashlib.sha256(case_id.encode()).hexdigest()[:20])
    except WaveformError as exc:
        raise HTTPException(exc.status,detail={'code':exc.code,'message':str(exc)})
    except OSError:
        raise HTTPException(503,detail={'code':'WAVEFORM_READ_FAILED','message':'Stored audio bytes could not be read.'}) from None
    finally:
        MEDIA_INSPECTION_LOCK.release()
    result.update(artifactId=artifact_id,caseId=case_id)
    return {'data':result}


@app.get("/api/v1/cases/{case_id}/artifacts/{artifact_id}/audio-screen")
def read_audio_screen(case_id: str, artifact_id: str):
    get_case(case_id)
    with connect() as db:
        artifact = db.execute('SELECT 1 FROM artifact_files WHERE case_id=? AND artifact_id=?',(case_id,artifact_id)).fetchone()
        if not artifact:
            raise HTTPException(404, detail='Uploaded artifact not found in this case.')
        row = db.execute('SELECT result_json FROM audio_screenings WHERE case_id=? AND artifact_id=? ORDER BY created_at DESC LIMIT 1',(case_id,artifact_id)).fetchone()
    return {'data':json.loads(row['result_json']) if row else None}


@app.post("/api/v1/cases/{case_id}/artifacts/{artifact_id}/audio-screen")
def create_audio_screen(case_id: str, artifact_id: str, body: dict[str, Any], idempotency_key: str | None = Header(default=None,alias='Idempotency-Key')):
    get_case(case_id)
    if body.get('acceptExperimental') is not True:
        raise HTTPException(422, detail='This research audio-only screen requires explicit experimental acknowledgement.')
    with connect() as db:
        cached = idempotent_response(db,case_id,idempotency_key)
        if cached:
            return cached
        row = db.execute('SELECT stored_path,sha256,media_type FROM artifact_files WHERE case_id=? AND artifact_id=?',(case_id,artifact_id)).fetchone()
    if not row or row['media_type'] not in {'Audio','Video'}:
        raise HTTPException(404, detail='Uploaded audio/video was not found in this case.')
    if not MEDIA_INSPECTION_LOCK.acquire(blocking=False):
        raise HTTPException(409, detail='Another media operation is running. Try again shortly.')
    try:
        root = DATA_ROOT/'evidence'/hashlib.sha256(case_id.encode()).hexdigest()[:20]
        result = screen_audio(Path(row['stored_path']),row['sha256'],root)
        ident, stamp = 'AUD-'+uuid.uuid4().hex[:16], now()
        result.update(id=ident,artifactId=artifact_id,caseId=case_id,createdAt=stamp)
        response = {'data':result}
        with connect() as db:
            db.execute('INSERT INTO audio_screenings VALUES(?,?,?,?,?)',(ident,case_id,artifact_id,json.dumps(result),stamp))
            audit(db,case_id,'audio.research_screen_completed','artifact',artifact_id,{'screenId':ident,'scope':result['scope'],'validated':False})
            save_idempotency(db,case_id,idempotency_key,response)
        return response
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from None
    except Exception:
        raise HTTPException(503, detail='Research audio model or decoder failed. No scores were substituted.') from None
    finally:
        MEDIA_INSPECTION_LOCK.release()


@app.get("/api/v1/cases/{case_id}/artifacts/{artifact_id}/preview")
def preview_media(case_id: str, artifact_id: str):
    get_case(case_id)
    with connect() as db:
        row = db.execute('SELECT stored_path,media_type,sha256 FROM artifact_files WHERE case_id=? AND artifact_id=?',(case_id,artifact_id)).fetchone()
    if row is None:
        raise HTTPException(404, detail='Uploaded media was not found in this case.')
    path = Path(row['stored_path']).resolve()
    root = DATA_ROOT/'evidence'/hashlib.sha256(case_id.encode()).hexdigest()[:20]
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise HTTPException(404, detail='Stored bytes are unavailable.')
    if path.stat().st_size > MAX_UPLOAD_BYTES:
        raise HTTPException(413, detail='Media exceeds the preview size limit.')
    digest, total = hashlib.sha256(), 0
    with path.open('rb') as source:
        header = source.read(16)
        source.seek(0)
        for chunk in iter(lambda: source.read(1024*1024), b''):
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                raise HTTPException(413, detail='Media exceeds the preview size limit.')
            digest.update(chunk)
    if digest.hexdigest() != row['sha256']:
        raise HTTPException(409, detail='Stored media differs from its registered digest.')
    mime = None
    if row['media_type'] == 'Video':
        if header[4:8] == b'ftyp': mime = 'video/mp4'
        elif header[:4] == b'\x1aE\xdf\xa3': mime = 'video/webm'
    elif row['media_type'] == 'Audio' and header[:4] == b'RIFF' and header[8:12] == b'WAVE':
        mime = 'audio/wav'
    elif row['media_type'] == 'Image':
        if header[:8] == b'\x89PNG\r\n\x1a\n': mime = 'image/png'
        elif header[:3] == b'\xff\xd8\xff': mime = 'image/jpeg'
    if not mime:
        raise HTTPException(422, detail='Preview supports MP4, WebM, WAV, PNG and JPEG. Other files can be downloaded for external tools.')
    return FileResponse(path, media_type=mime, headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-Content-SHA256':row['sha256']})


@app.get("/api/v1/cases/{case_id}/artifacts/{artifact_id}/audio-preview")
def preview_pcm_audio(case_id: str, artifact_id: str):
    get_case(case_id)
    with connect() as db:
        row=db.execute('SELECT stored_path,media_type FROM artifact_files WHERE case_id=? AND artifact_id=?',(case_id,artifact_id)).fetchone()
    if row is None or row['media_type']!='Audio':
        raise HTTPException(404,detail={'code':'AUDIO_NOT_FOUND','message':'Uploaded audio was not found in this case.'})
    path=Path(row['stored_path']).resolve()
    root=DATA_ROOT/'evidence'/hashlib.sha256(case_id.encode()).hexdigest()[:20]
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise HTTPException(404,detail={'code':'AUDIO_NOT_FOUND','message':'Stored audio bytes are unavailable.'})
    with path.open('rb') as source:header=source.read(12)
    if header[:4]!=b'RIFF' or header[8:12]!=b'WAVE':
        raise HTTPException(422,detail={'code':'UNSUPPORTED_WAV','message':'This preview supports WAV audio only.'})
    return FileResponse(path,media_type='audio/wav',headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})


@app.get("/api/v1/cases/{case_id}/artifacts/{artifact_id}/download")
def download_artifact(case_id: str, artifact_id: str):
    get_case(case_id)
    with connect() as db:
        row = db.execute("SELECT original_name,sha256,stored_path FROM artifact_files WHERE case_id=? AND artifact_id=?", (case_id, artifact_id)).fetchone()
    if not row or not Path(row["stored_path"]).is_file():
        raise HTTPException(404, detail={"code": "ARTIFACT_BYTES_NOT_FOUND", "message": "Stored bytes were not found for this artifact."})
    return FileResponse(row["stored_path"], filename=row["original_name"], headers={"X-Content-SHA256": row["sha256"], "Cache-Control": "no-store"})


def write_record(case_id: str, kind: str, body: dict[str, Any], key: str, status: str) -> dict[str, Any]:
    get_case(case_id)
    with connect() as db:
        cached = idempotent_response(db, case_id, key)
        if cached:
            return cached
        ident, stamp = f"{kind[:3].upper()}-{uuid.uuid4().hex[:10].upper()}", now()
        response = {"data": {"id": ident, "message": f"{kind.title()} saved in the local case database.", "status": status}}
        db.execute("INSERT INTO case_records VALUES(?,?,?,?,?,?)", (ident, case_id, kind, status, json.dumps(body), stamp))
        audit(db, case_id, f"{kind}.created", kind, ident, body)
        save_idempotency(db, case_id, key, response)
        return response


@app.post("/api/v1/cases/{case_id}/reviews/{review_id}/decision")
def review_decision(case_id: str, review_id: str, body: dict[str, Any], idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    if body.get("decision") not in {"reviewed", "returned", "abstained"}:
        raise HTTPException(422, detail={"code": "INVALID_DECISION", "message": "Decision must be reviewed, returned, or abstained."})
    snapshot = get_case(case_id)
    if not any(item["id"] == review_id for item in snapshot["reviewItems"]):
        raise HTTPException(404, detail={"code": "REVIEW_NOT_FOUND", "message": "This review item is not open in the selected case."})
    with connect() as db:
        cached = idempotent_response(db, case_id, idempotency_key)
        if cached:
            return cached
        ident, stamp = str(uuid.uuid4()), now()
        payload = {"decision": body["decision"], "note": str(body.get("note", ""))[:4000]}
        db.execute("INSERT INTO review_decisions VALUES(?,?,?,?,?,?,?)", (ident, case_id, review_id, payload["decision"], payload["note"], "local-development-user", stamp))
        audit(db, case_id, "review.decision_recorded", "review", review_id, payload)
        response = {"data": {"id": ident, "message": "Examiner decision recorded in the append-only review log."}}
        save_idempotency(db, case_id, idempotency_key, response)
        return response


@app.post("/api/v1/cases/{case_id}/acquisitions")
def create_acquisition(case_id: str, body: dict[str, Any], idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    required = ("sourceConnector", "fromUtc", "toUtc", "reason", "handling")
    if any(not body.get(field) for field in required):
        raise HTTPException(422, detail={"code": "INVALID_ACQUISITION", "message": "All acquisition request fields are required."})
    return write_record(case_id, "acquisition", body, idempotency_key, "awaiting_authorization")


@app.post("/api/v1/cases/{case_id}/reports")
def create_report(case_id: str, body: dict[str, Any], idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    if not body.get("title") or not body.get("template") or not body.get("scope"):
        raise HTTPException(422, detail={"code": "INVALID_REPORT", "message": "Title, template, and scope are required."})
    return write_record(case_id, "report", body, idempotency_key, "draft")


@app.post("/api/v1/cases/{case_id}/reports/from-summary")
def create_cited_report(case_id: str, body: dict[str, Any], idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    snapshot = get_case(case_id)
    title, episode_id = body.get("title"), body.get("summaryEpisodeId")
    if (set(body) != {"title", "summaryEpisodeId"} or not isinstance(title, str) or not 1 <= len(title.strip()) <= 160 or
            not isinstance(episode_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", episode_id)):
        raise HTTPException(422, detail={"code": "INVALID_CITED_REPORT", "message": "Provide a title up to 160 characters and a saved summaryEpisodeId."})
    if not idempotency_key or len(idempotency_key) > 200:
        raise HTTPException(400, detail={"code": "IDEMPOTENCY_KEY_REQUIRED", "message": "Provide an Idempotency-Key for this report."})
    operation_key = "cited-report:" + hashlib.sha256(idempotency_key.encode()).hexdigest()
    request_digest = content_digest(body)
    with connect() as db:
        cached = idempotent_response(db, case_id, operation_key)
        if cached:
            if cached.get("requestDigest") != request_digest:
                raise HTTPException(409, detail={"code": "IDEMPOTENCY_CONFLICT", "message": "This report key belongs to different request parameters."})
            return cached
    graph = CaseGraph(case_id)
    if not graph.available:
        raise HTTPException(503, detail={"code": "FALKORDB_UNAVAILABLE", "message": "FalkorDB is required to read the saved summary for a new report."})
    try:
        episode = graph.get_episode(episode_id)
        if episode is None:
            raise HTTPException(404, detail={"code": "SUMMARY_NOT_FOUND", "message": "The summary episode is not present in this case."})
        ident, stamp = scoped_record_id(case_id, operation_key, "RPT"), now()
        envelope = build_report(snapshot, episode, report_id=ident, title=title.strip(), created_at=stamp)
    except ValueError as exc:
        raise HTTPException(422, detail={"code": "REPORT_VERIFICATION_FAILED", "message": str(exc)})
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, detail={"code": "REPORT_SOURCE_UNAVAILABLE", "message": "The saved summary could not be loaded and verified."}) from None
    response = {"data": {"id": ident, "title": title.strip(), "status": "unreviewed_draft", "createdAt": stamp,
                          "summaryEpisodeId": episode_id, "contentSha256": envelope["contentSha256"]}, "requestDigest": request_digest}
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        cached = idempotent_response(db, case_id, operation_key)
        if cached:
            if cached.get("requestDigest") != request_digest:
                raise HTTPException(409, detail={"code": "IDEMPOTENCY_CONFLICT", "message": "This report key belongs to different request parameters."})
            return cached
        db.execute("INSERT INTO report_snapshots VALUES(?,?,?,?,?,?,?)", (ident, case_id, title.strip(), episode_id, json.dumps(envelope, ensure_ascii=False), envelope["contentSha256"], stamp))
        audit(db, case_id, "report.cited_draft_created", "report", ident, {"summaryEpisodeId": episode_id, "contentSha256": envelope["contentSha256"], "sourceIds": envelope["report"]["sources"]})
        save_idempotency(db, case_id, operation_key, response)
    return response


def stored_report(case_id: str, report_id: str) -> dict:
    get_case(case_id)
    with connect() as db:
        row = db.execute("SELECT envelope_json,content_sha256 FROM report_snapshots WHERE case_id=? AND id=?", (case_id, report_id)).fetchone()
    if row is None:
        raise HTTPException(404, detail={"code": "REPORT_NOT_FOUND", "message": "The cited report is not present in this case."})
    try:
        envelope = json.loads(row["envelope_json"])
        if content_digest(envelope["report"]) != row["content_sha256"] or envelope.get("contentSha256") != row["content_sha256"]:
            raise ValueError("Digest mismatch")
    except (ValueError, KeyError, TypeError):
        raise HTTPException(409, detail={"code": "REPORT_INTEGRITY_FAILED", "message": "The saved report content no longer matches its recorded digest."}) from None
    return envelope


@app.get("/api/v1/cases/{case_id}/reports/{report_id}")
def read_cited_report(case_id: str, report_id: str):
    return {"data": stored_report(case_id, report_id)}


@app.get("/api/v1/cases/{case_id}/reports/{report_id}/export/{format}")
def export_cited_report(case_id: str, report_id: str, format: str):
    if format not in {"html", "json"}:
        raise HTTPException(422, detail={"code": "UNSUPPORTED_REPORT_FORMAT", "message": "Choose HTML preview or JSON export."})
    envelope = stored_report(case_id, report_id)
    headers = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
    if format == "html":
        headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'"
        return HTMLResponse(render_html(envelope), headers=headers)
    headers["Content-Disposition"] = f'attachment; filename="{envelope["report"]["reportId"]}.json"'
    return Response(json.dumps(envelope, indent=2, ensure_ascii=False), media_type="application/json", headers=headers)


@app.post("/api/v1/cases/{case_id}/exports")
def create_export(case_id: str, body: dict[str, Any], idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    if body.get("contents") not in {"brief", "manifest", "timeline"} or body.get("format") not in {"pdf-json", "pdf", "json-csv"}:
        raise HTTPException(422, detail={"code": "INVALID_EXPORT", "message": "Choose a supported package content and format."})
    return write_record(case_id, "export", body, idempotency_key, "queued_for_generation")


@app.post("/api/v1/cases/{case_id}/media-runs")
def create_media_run(case_id: str, body: dict[str, Any], idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    snapshot = get_case(case_id)
    artifact_id = body.get("artifactId")
    artifact = next((item for item in snapshot["evidence"] if item["id"] == artifact_id), None)
    if not artifact:
        raise HTTPException(404, detail={"code": "ARTIFACT_NOT_FOUND", "message": "The selected artifact is not registered in this case."})
    if not any(x in artifact.get("type", "").lower() for x in ("video", "audio", "image", "media")):
        raise HTTPException(422, detail={"code": "UNSUPPORTED_MEDIA", "message": "This artifact is not registered as supported media."})
    with connect() as db:
        cached = idempotent_response(db, case_id, idempotency_key)
        if cached:
            return cached
        run_id, stamp = f"RUN-{uuid.uuid4().hex[:10].upper()}", now()
        result = {"signals": [], "error": {"code": "NO_VALIDATED_MODEL", "message": "No validated media detector is configured; no score or manipulation claim was produced."}}
        db.execute("INSERT INTO media_runs VALUES(?,?,?,?,?,?,?,?)", (run_id, case_id, artifact_id, "failed", json.dumps(body), json.dumps(result), stamp, stamp))
        audit(db, case_id, "media_run.blocked_no_model", "media_run", run_id, {"artifactId": artifact_id, "profile": body.get("profile")})
        response = {"data": {"id": run_id, "message": result["error"]["message"], "status": "failed"}}
        save_idempotency(db, case_id, idempotency_key, response)
        return response


@app.get("/api/v1/cases/{case_id}/graph/entities")
def graph_entities(case_id: str, limit: int = Query(default=100, ge=1, le=250)):
    get_case(case_id)
    graph = CaseGraph(case_id)
    if not graph.available:
        raise HTTPException(503, detail={"code": "FALKORDB_UNAVAILABLE", "message": "The case relationship graph is not connected. Start FalkorDB to use graph-backed context."})
    return {"data": {"items": graph.list_entities(limit)}}


@app.post("/api/v1/cases/{case_id}/context/ask")
def context_agent(case_id: str, body: dict[str, Any], idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    snapshot = get_case(case_id)
    entity_id = body.get("entityId", "")
    question = body.get("question", "")
    depth = body.get("depth", 3)
    with connect() as db:
        cached = idempotent_response(db, case_id, idempotency_key)
        if cached:
            return cached
    graph = CaseGraph(case_id)
    if not graph.available:
        with connect() as db:
            audit(db, case_id, "agent.graph_context_unavailable", "entity", str(entity_id)[:100], {"questionLength": len(str(question)), "dependency": "FalkorDB"})
        raise HTTPException(503, detail={"code": "FALKORDB_UNAVAILABLE", "message": "The graph context agent requires FalkorDB; no disconnected or synthetic answer was substituted."})
    known_source_ids = {str(item.get("id")) for item in snapshot.get("evidence", []) if item.get("id")}
    result = run_context_orchestrator(entity_id=entity_id, question=question, depth=depth, graph=graph, known_source_ids=known_source_ids)
    if result.get("status") == "invalid":
        raise HTTPException(422, detail=result["error"])
    if result.get("memoryKind") == "episodic_unverified":
        try:
            graph.remember_episode(episode_id=scoped_record_id(case_id, idempotency_key, "EP"), agent_id="context-planner",
                                  kind="graph-question", summary=str(question), evidence_state=result.get("state", "unknown"),
                                  source_ids=result.get("sources", []),
                                  payload={"entityId": str(entity_id), "question": str(question), "answer": result.get("answer", ""), "result": result},
                                  idempotency_key=idempotency_key)
        except Exception:
            raise HTTPException(503, detail={"code": "AGENT_MEMORY_WRITE_FAILED", "message": "The graph answer could not be retained as case-scoped episodic memory."})
    with connect() as db:
        # SQLite stores the audit/idempotency trail; FalkorDB owns agent memory.
        audit(db, case_id, "agent.graph_context_queried", "entity", str(entity_id), {"questionLength": len(str(question)), "pathCount": len(result.get("paths", [])), "sources": result.get("sources", []), "agent": result.get("agent", {}).get("id"), "verification": result.get("verification", {}).get("ok")})
        response = {"data": result}
        save_idempotency(db, case_id, idempotency_key, response)
        return response


@app.get("/api/v1/cases/{case_id}/context/memory")
def context_memory(case_id: str, limit: int = Query(default=20, ge=1, le=100)):
    get_case(case_id)
    graph = CaseGraph(case_id)
    if not graph.available:
        raise HTTPException(503, detail={"code": "FALKORDB_UNAVAILABLE", "message": "FalkorDB is required to read persistent agent memory."})
    try:
        episodes = graph.list_episodes(limit=limit, agent_id="context-planner")
    except Exception:
        raise HTTPException(503, detail={"code": "AGENT_MEMORY_UNAVAILABLE", "message": "FalkorDB could not read this case's episodic memory."})
    items = []
    for episode in episodes:
        payload = episode.get("payload", {})
        items.append({"id": episode["id"], "agentId": episode["agentId"], "entityId": payload.get("entityId", ""),
                      "question": payload.get("question", episode.get("summary", "")), "answer": payload.get("answer", ""),
                      "sources": episode.get("sourceIds", []), "result": payload.get("result", {}), "createdAt": episode.get("createdAt")})
    return {"data": {"items": items}}


# The local development server can host its matching frontend on the same origin.
# API routes above take precedence; production deployments should use a real static host.
app.mount("/", StaticFiles(directory=UI_ROOT, html=True), name="frontend")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local Forensic Atlas development API")
    parser.add_argument("--seed-demo", action="store_true", help="Insert the clearly fictional Northstar demo snapshot if absent")
    parser.add_argument("--sync-demo-graph", action="store_true", help="Merge the fictional case graph without erasing agent memory or handoffs")
    args = parser.parse_args()
    if args.seed_demo or args.sync_demo_graph:
        initialize(seed_demo=True)
        if args.seed_demo:
            print("Seeded fictional case DF-24-017 into the local SQLite database.")
        if args.sync_demo_graph:
            graph = CaseGraph("DF-24-017")
            if not graph.available:
                raise SystemExit("FalkorDB is unavailable. Start it and retry --sync-demo-graph.")
            graph.upsert_demo_projection(json.loads(DEMO_PATH.read_text(encoding="utf-8-sig")))
            print("Loaded the clearly fictional case graph into its isolated FalkorDB graph.")
    host = os.getenv("SUTRAM_API_HOST", "127.0.0.1")
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("This development service only binds to loopback. Add reviewed authentication before exposing it.")
    import uvicorn

    uvicorn.run("backend.app:app", host=host, port=int(os.getenv("SUTRAM_API_PORT", "8100")), reload=False)


if __name__ == "__main__":
    main()
