"""Case-scoped FalkorDB projection and explainable graph traversal tools."""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Any


def graph_name(case_id: str) -> str:
    # FalkorDB graph names are isolated per case; keep raw identifiers out of names.
    suffix = hashlib.sha256(case_id.encode("utf-8")).hexdigest()[:16]
    return f"sutram_case_{suffix}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class CaseGraph:
    def __init__(self, case_id: str):
        self.case_id = case_id
        self.graph = None
        self.error = None
        url = os.getenv("FALKORDB_URL", "redis://127.0.0.1:6380")
        try:
            from falkordb import FalkorDB

            db = FalkorDB(url=url, socket_connect_timeout=1, socket_timeout=2)
            self.graph = db.select_graph(graph_name(case_id))
            self.graph.query("RETURN 1 AS ready")
        except Exception as exc:  # health endpoints report unavailability without leaking config
            self.graph = None
            self.error = type(exc).__name__

    @property
    def available(self) -> bool:
        return self.graph is not None

    def upsert_demo_projection(self, snapshot: dict[str, Any]) -> None:
        """Merge the fictional projection without erasing memory or handoffs."""
        if not self.graph:
            raise RuntimeError("FalkorDB is not connected.")
        if self.case_id != "DF-24-017" or snapshot.get("case", {}).get("id") != self.case_id:
            raise ValueError("Demo projection is limited to the fictional Northstar case.")
        # Create artifact references for every fixture source, including sources
        # with no entity links yet. They anchor SUPPORTED_BY provenance edges.
        for artifact in snapshot.get("evidence", []):
            self.graph.query(
                "MERGE (a:CaseEntity {caseId:$caseId,id:$id}) "
                "ON CREATE SET a.label='Artifact',a.name=$name,a.source=$id,a.claim='observed'",
                params={"caseId": self.case_id, "id": artifact["id"], "name": artifact["name"]},
            )
        entities = [
            {"id": "SES-0942", "label": "Session", "name": "09:42 sign-in", "source": "ART-028", "claim": "observed"},
            {"id": "ACC-TEMP", "label": "Account", "name": "analyst-temp", "source": "ART-028", "claim": "observed"},
            {"id": "DEV-114", "label": "Device", "name": "WS-114", "source": "ART-028", "claim": "observed"},
            {"id": "ART-025", "label": "Artifact", "name": "meeting-clip-raw.mp4", "source": "ART-025", "claim": "observed"},
            {"id": "FILE-Q4", "label": "Artifact", "name": "Q4-planning.zip", "source": "ART-028", "claim": "observed"},
            {"id": "IP-1042", "label": "NetworkEndpoint", "name": "10.42.8.19", "source": "ART-026", "claim": "observed"},
        ]
        for entity in entities:
            self.graph.query(
                "MERGE (n:CaseEntity {caseId:$caseId,id:$id}) "
                "ON CREATE SET n.label=$label,n.name=$name,n.source=$source,n.claim=$claim",
                params={"caseId": self.case_id, **entity},
            )
        edges = [
            ("SES-0942", "ACC-TEMP", "AUTHENTICATED_AS", "observed", "ART-028"),
            ("SES-0942", "DEV-114", "OBSERVED_ON", "observed", "ART-028"),
            ("SES-0942", "FILE-Q4", "DOWNLOADED", "observed", "ART-028"),
            ("ACC-TEMP", "DEV-114", "USED", "observed", "ART-028"),
            ("FILE-Q4", "IP-1042", "TRANSFERRED_FROM", "candidate", "ART-026"),
        ]
        for source_id, target_id, relation, state, artifact_id in edges:
            # Relation type is validated against a fixed allowlist before interpolation.
            if not re.fullmatch(r"[A-Z_]+", relation):
                raise ValueError("Invalid graph relationship type.")
            self.graph.query(
                "MATCH (a:CaseEntity {caseId:$caseId,id:$sourceId}), (b:CaseEntity {caseId:$caseId,id:$targetId}) "
                f"MERGE (a)-[:{relation} {{caseId:$caseId,state:$state,artifactId:$artifactId}}]->(b)",
                params={"caseId": self.case_id, "sourceId": source_id, "targetId": target_id, "state": state, "artifactId": artifact_id},
            )

    def list_entities(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.graph:
            raise RuntimeError("FalkorDB is not connected.")
        result = self.graph.query(
            "MATCH (n:CaseEntity {caseId:$caseId}) RETURN n.id,n.label,n.name,n.source,n.claim LIMIT $limit",
            params={"caseId": self.case_id, "limit": max(1, min(limit, 250))},
        )
        return [dict(zip(("id", "label", "name", "source", "claim"), row)) for row in result.result_set]

    def list_relationships(self) -> list[dict[str, Any]]:
        if not self.graph:
            raise RuntimeError("FalkorDB is not connected.")
        result = self.graph.query(
            "MATCH (a:CaseEntity {caseId:$caseId})-[r]->(b:CaseEntity {caseId:$caseId}) "
            "RETURN a.id,b.id,type(r),r.state,r.artifactId LIMIT 200",
            params={"caseId": self.case_id},
        )
        return [dict(zip(('from','to','label','state','source'), row)) for row in result.result_set]

    def explain_entity(self, entity_id: str, depth: int = 3) -> list[dict[str, Any]]:
        """Return bounded, source-labelled graph paths; the caller never executes generated Cypher."""
        if not self.graph:
            raise RuntimeError("FalkorDB is not connected.")
        safe_depth = max(1, min(int(depth), 3))
        result = self.graph.query(
            "MATCH p=(s:CaseEntity {caseId:$caseId,id:$entityId})-[:AUTHENTICATED_AS|OBSERVED_ON|DOWNLOADED|USED|TRANSFERRED_FROM*1.." + str(safe_depth) + "]-(t:CaseEntity {caseId:$caseId}) "
            "RETURN [n IN nodes(p) | {id:n.id,label:n.label,name:n.name,source:n.source,claim:n.claim}] AS nodes, "
            "[r IN relationships(p) | {type:type(r),state:r.state,artifactId:r.artifactId}] AS links LIMIT 25",
            params={"caseId": self.case_id, "entityId": entity_id},
        )
        return [{"nodes": row[0], "links": row[1]} for row in result.result_set]

    def remember_episode(self, *, episode_id: str, agent_id: str, kind: str, summary: str,
                         evidence_state: str, source_ids: list[str], payload: dict[str, Any],
                         idempotency_key: str, created_at: str | None = None) -> dict[str, Any]:
        """Persist a bounded, case-scoped episodic record. It never promotes facts."""
        if not self.graph:
            raise RuntimeError("FalkorDB is not connected.")
        if evidence_state not in {"observed", "derived", "candidate", "hypothesis", "unknown"}:
            raise ValueError("Unsupported evidence state.")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", agent_id):
            raise ValueError("Invalid agent ID.")
        clean_sources = sorted({str(item) for item in source_ids if re.fullmatch(r"ART-[A-Z0-9-]{1,32}", str(item))})[:100]
        stamp = created_at or _now()
        payload_json = json.dumps(payload, ensure_ascii=False)
        if len(payload_json) > 16000:
            raise ValueError("Episode payload exceeds the 16 KB memory limit.")
        self.graph.query(
            "MERGE (e:AgentEpisode {id:$id,caseId:$caseId}) "
            "ON CREATE SET e.agentId=$agentId,e.kind=$kind,e.summary=$summary,e.evidenceState=$state,"
            "e.sourceIdsJson=$sources,e.payloadJson=$payload,e.idempotencyKey=$key,e.createdAt=$createdAt,e.version=1 "
            "RETURN e.id,e.createdAt,e.version",
            params={"id": episode_id, "caseId": self.case_id, "agentId": agent_id, "kind": kind[:48],
                    "summary": summary[:2000], "state": evidence_state, "sources": json.dumps(clean_sources),
                    "payload": payload_json, "key": idempotency_key[:200], "createdAt": stamp},
        )
        run_id = payload.get("runId") if isinstance(payload, dict) and kind == "case-synthesis" else None
        if isinstance(run_id, str) and run_id:
            self.graph.query(
                "MATCH (e:AgentEpisode {id:$episodeId,caseId:$caseId}) "
                "MERGE (r:AgentRun {id:$runId,caseId:$caseId}) "
                "ON CREATE SET r.agentId=$agentId,r.createdAt=$createdAt "
                "MERGE (r)-[:RECORDED_AS {caseId:$caseId}]->(e) RETURN r.id",
                params={"episodeId": episode_id, "caseId": self.case_id, "runId": run_id,
                        "agentId": agent_id, "createdAt": stamp},
            )
        if clean_sources:
            self.graph.query(
                "MATCH (e:AgentEpisode {id:$id,caseId:$caseId}) UNWIND $sources AS sourceId "
                "MERGE (a:CaseEntity {caseId:$caseId,id:sourceId}) "
                "ON CREATE SET a.label='Artifact',a.name=sourceId,a.source=sourceId,a.claim='derived' "
                "MERGE (e)-[:SUPPORTED_BY {caseId:$caseId}]->(a) RETURN count(a)",
                params={"id": episode_id, "caseId": self.case_id, "sources": clean_sources},
            )
        return {"id": episode_id, "caseId": self.case_id, "agentId": agent_id, "kind": kind,
                "summary": summary[:2000], "evidenceState": evidence_state, "sourceIds": clean_sources,
                "payload": payload, "createdAt": stamp, "version": 1}

    def list_episodes(self, limit: int = 20, agent_id: str | None = None) -> list[dict[str, Any]]:
        """Read recent episodes through fixed query templates with a hard cap."""
        if not self.graph:
            raise RuntimeError("FalkorDB is not connected.")
        safe_limit = max(1, min(int(limit), 100))
        if agent_id is not None:
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", agent_id):
                raise ValueError("Invalid agent ID.")
            query = ("MATCH (e:AgentEpisode {caseId:$caseId,agentId:$agentId}) "
                     "RETURN e.id,e.agentId,e.kind,e.summary,e.evidenceState,e.sourceIdsJson,e.payloadJson,e.createdAt,e.version "
                     "ORDER BY e.createdAt DESC LIMIT $limit")
            params = {"caseId": self.case_id, "agentId": agent_id, "limit": safe_limit}
        else:
            query = ("MATCH (e:AgentEpisode {caseId:$caseId}) "
                     "RETURN e.id,e.agentId,e.kind,e.summary,e.evidenceState,e.sourceIdsJson,e.payloadJson,e.createdAt,e.version "
                     "ORDER BY e.createdAt DESC LIMIT $limit")
            params = {"caseId": self.case_id, "limit": safe_limit}
        result = self.graph.query(query, params=params)
        keys = ("id", "agentId", "kind", "summary", "evidenceState", "sourceIdsJson", "payloadJson", "createdAt", "version")
        items = []
        for values in result.result_set:
            row = dict(zip(keys, values))
            try:
                row["sourceIds"] = json.loads(row.pop("sourceIdsJson") or "[]")
                row["payload"] = json.loads(row.pop("payloadJson") or "{}")
            except (TypeError, json.JSONDecodeError):
                continue
            row["caseId"] = self.case_id
            items.append(row)
        return items

    def get_episode(self, episode_id: str) -> dict[str, Any] | None:
        if not self.graph:
            raise RuntimeError("FalkorDB is not connected.")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", episode_id):
            raise ValueError("Invalid episode ID.")
        result = self.graph.query(
            "MATCH (e:AgentEpisode {caseId:$caseId,id:$id}) "
            "RETURN e.id,e.agentId,e.kind,e.summary,e.evidenceState,e.sourceIdsJson,e.payloadJson,e.createdAt,e.version LIMIT 1",
            params={"caseId": self.case_id, "id": episode_id})
        if not result.result_set:
            return None
        row = dict(zip(("id", "agentId", "kind", "summary", "evidenceState", "sourceIdsJson", "payloadJson", "createdAt", "version"), result.result_set[0]))
        row["sourceIds"] = json.loads(row.pop("sourceIdsJson") or "[]")
        row["payload"] = json.loads(row.pop("payloadJson") or "{}")
        row["caseId"] = self.case_id
        return row

    def create_handoff(self, *, handoff_id: str, from_agent: str, to_agent: str,
                       task: str, state: str, source_ids: list[str], context: dict[str, Any],
                       idempotency_key: str, run_id: str | None = None,
                       created_at: str | None = None) -> dict[str, Any]:
        """Record a shared, auditable handoff as graph state; no automatic dispatch."""
        if not self.graph:
            raise RuntimeError("FalkorDB is not connected.")
        for value in (from_agent, to_agent):
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", value):
                raise ValueError("Invalid agent ID.")
        if state not in {"candidate", "hypothesis", "unknown", "derived"}:
            raise ValueError("Unsupported handoff state.")
        clean_sources = sorted({str(item) for item in source_ids if re.fullmatch(r"ART-[A-Z0-9-]{1,32}", str(item))})[:100]
        stamp = created_at or _now()
        context_json = json.dumps(context, ensure_ascii=False)
        if len(context_json) > 12000:
            raise ValueError("Handoff context exceeds the 12 KB limit.")
        self.graph.query(
            "MERGE (h:AgentHandoff {id:$id,caseId:$caseId}) "
            "ON CREATE SET h.fromAgent=$fromAgent,h.toAgent=$toAgent,h.task=$task,h.state=$state,"
            "h.sourceIdsJson=$sources,h.contextJson=$context,h.idempotencyKey=$key,h.createdAt=$createdAt,"
            "h.status='pending',h.version=1 "
            "WITH h MERGE (a:AgentIdentity {id:$fromAgent,caseId:$caseId}) "
            "MERGE (b:AgentIdentity {id:$toAgent,caseId:$caseId}) "
            "MERGE (r:AgentRun {id:$runId,caseId:$caseId}) "
            "ON CREATE SET r.agentId=$fromAgent,r.createdAt=$createdAt "
            "MERGE (a)-[:HANDED_OFF_TO {caseId:$caseId}]->(h) "
            "MERGE (r)-[:HANDED_OFF_TO {caseId:$caseId}]->(h) "
            "MERGE (h)-[:ASSIGNED_TO {caseId:$caseId}]->(b) "
            "RETURN h.id,h.createdAt,h.status",
            params={"id": handoff_id, "caseId": self.case_id, "fromAgent": from_agent, "toAgent": to_agent,
                    "task": task[:500], "state": state, "sources": json.dumps(clean_sources),
                    "context": context_json,
                    "key": idempotency_key[:200], "runId": run_id or handoff_id, "createdAt": stamp},
        )
        if clean_sources:
            self.graph.query(
                "MATCH (h:AgentHandoff {id:$id,caseId:$caseId}) UNWIND $sources AS sourceId "
                "MATCH (a:CaseEntity {caseId:$caseId,id:sourceId}) "
                "MERGE (h)-[:SUPPORTED_BY {caseId:$caseId}]->(a) RETURN count(a)",
                params={"id": handoff_id, "caseId": self.case_id, "sources": clean_sources},
            )
        return {"id": handoff_id, "caseId": self.case_id, "fromAgent": from_agent, "toAgent": to_agent,
                "task": task[:500], "state": state, "sourceIds": clean_sources, "context": context,
                "createdAt": stamp, "status": "pending", "version": 1}

    def list_handoffs(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self.graph:
            raise RuntimeError("FalkorDB is not connected.")
        result = self.graph.query(
            "MATCH (h:AgentHandoff {caseId:$caseId}) "
            "RETURN h.id,h.fromAgent,h.toAgent,h.task,h.state,h.sourceIdsJson,h.contextJson,h.createdAt,h.status,h.version,h.acknowledgedAt "
            "ORDER BY h.createdAt DESC LIMIT $limit",
            params={"caseId": self.case_id, "limit": max(1, min(int(limit), 100))},
        )
        keys = ("id", "fromAgent", "toAgent", "task", "state", "sourceIdsJson", "contextJson", "createdAt", "status", "version", "acknowledgedAt")
        items = []
        for values in result.result_set:
            row = dict(zip(keys, values))
            try:
                row["sourceIds"] = json.loads(row.pop("sourceIdsJson") or "[]")
                row["context"] = json.loads(row.pop("contextJson") or "{}")
            except (TypeError, json.JSONDecodeError):
                continue
            row["caseId"] = self.case_id
            items.append(row)
        return items

    def acknowledge_handoff(self, handoff_id: str, expected_version: int, idempotency_key: str) -> dict[str, Any] | None:
        """Optimistic state transition; stale acknowledgements never overwrite newer state."""
        if not self.graph:
            raise RuntimeError("FalkorDB is not connected.")
        if not re.fullmatch(r"HO-[a-f0-9]{24}", handoff_id) or expected_version < 1:
            raise ValueError("Invalid handoff ID or version.")
        existing = self.graph.query(
            "MATCH (h:AgentHandoff {id:$id,caseId:$caseId,status:'acknowledged',ackIdempotencyKey:$key}) "
            "RETURN h.id,h.status,h.version,h.acknowledgedAt",
            params={"id": handoff_id, "caseId": self.case_id, "key": idempotency_key[:200]},
        )
        if existing.result_set:
            row = existing.result_set[0]
            return {"id": row[0], "status": row[1], "version": row[2], "acknowledgedAt": row[3]}
        result = self.graph.query(
            "MATCH (h:AgentHandoff {id:$id,caseId:$caseId,status:'pending',version:$expectedVersion}) "
            "SET h.status='acknowledged',h.version=h.version+1,h.acknowledgedAt=$acknowledgedAt,h.ackIdempotencyKey=$key "
            "RETURN h.id,h.status,h.version,h.acknowledgedAt",
            params={"id": handoff_id, "caseId": self.case_id, "expectedVersion": expected_version,
                    "acknowledgedAt": _now(), "key": idempotency_key[:200]},
        )
        if not result.result_set:
            return None
        row = result.result_set[0]
        return {"id": row[0], "status": row[1], "version": row[2], "acknowledgedAt": row[3]}
