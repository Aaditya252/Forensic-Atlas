"""Plan, run fixed tools, narrate only results, verify, and fall back safely."""
from __future__ import annotations

from typing import Any

from backend.agent_prompts import verify_output
from backend.agents.context_narrator import narrate_paths
from backend.agents.context_planner import plan_context_request


def run_context_orchestrator(
    *, entity_id: Any, question: Any, depth: Any, graph: Any,
    known_source_ids: set[str], narrator=narrate_paths,
) -> dict[str, Any]:
    plan = plan_context_request(entity_id, question, depth)
    if plan["status"] == "invalid":
        return {"status": "invalid", "error": {"code": plan["code"], "message": plan["message"]}}
    if plan["status"] == "refused":
        return {
            "status": "ok", "agent": {"id": "context-planner", "version": "0.1.0", "mode": "precise"},
            "question": str(question), "answer": "I can't determine that from graph retrieval. " + plan["safeReframe"],
            "state": "unknown", "sources": [], "statements": [], "observedNotes": [], "paths": [],
            "gap": {"state": "unknown", "message": "This request asks for a conclusion the graph agent is not permitted to make."},
            "refusal": {"reason": plan["reason"], "safeReframe": plan["safeReframe"]}, "trace": [],
        }
    if plan["status"] == "unsupported":
        return {
            "status": "ok", "agent": {"id": "context-planner", "version": "0.1.0", "mode": "precise"},
            "question": str(question), "answer": "The available graph tool cannot answer this request.",
            "state": "unknown", "sources": [], "statements": [], "observedNotes": [], "paths": [],
            "gap": {"state": "unknown", "message": "No configured tool covers this question; no case conclusion was produced."}, "trace": [],
        }

    call = plan["toolCalls"][0]
    raw_paths = graph.explain_entity(call["arguments"]["entityId"], call["arguments"]["depth"])
    output = narrator(call["arguments"]["entityId"], raw_paths, known_source_ids)
    output.update({
        "status": "ok", "agent": {"id": "context-narrator", "version": "0.1.0", "mode": "precise"},
        "question": str(question), "plan": plan["toolCalls"],
        "trace": [{"tool": call["tool"], "entityId": call["arguments"]["entityId"], "maxDepth": call["arguments"]["depth"], "pathCount": len(output.get("paths", []))}],
        "disclaimer": "Graph retrieval supports examiner review; it does not establish identity, intent, or causation.",
        "memoryKind": "episodic_unverified",
    })
    verification = verify_output(output, known_source_ids)
    if verification["ok"]:
        output["verification"] = {"ok": True, "agent": "context-verifier"}
        return output

    # Existing deterministic evidence-path-agent remains the required fallback.
    fallback = narrate_paths(call["arguments"]["entityId"], raw_paths, known_source_ids)
    fallback.update({
        "status": "ok", "agent": {"id": "evidence-path-agent", "version": "0.1.0", "mode": "precise-fallback"},
        "question": str(question), "plan": plan["toolCalls"],
        "trace": [{"tool": call["tool"], "entityId": call["arguments"]["entityId"], "maxDepth": call["arguments"]["depth"], "pathCount": len(fallback.get("paths", [])), "fallback": True}],
        "disclaimer": "Deterministic graph fallback; no identity, intent, or causation conclusion is produced.",
        "memoryKind": "episodic_unverified",
    })
    fallback_check = verify_output(fallback, known_source_ids)
    if fallback_check["ok"]:
        fallback["verification"] = {"ok": True, "agent": "context-verifier", "primaryAttempt": "rejected", "fallback": True}
        return fallback
    return {
        "status": "ok", "agent": {"id": "evidence-path-agent", "version": "0.1.0", "mode": "precise-fallback"},
        "question": str(question), "answer": "A source-linked answer could not be verified.", "state": "unknown",
        "sources": [], "statements": [], "observedNotes": [], "paths": [],
        "gap": {"state": "unknown", "message": "Both narration and deterministic fallback failed output verification; no answer was retained."},
        "trace": [{"tool": call["tool"], "fallback": True}],
        "verification": {"ok": False, "errors": fallback_check["errors"]},
    }
