"""Deterministic context request planner. No generated Cypher or SQL."""
from __future__ import annotations

import re
from typing import Any

_ENTITY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")
_FORBIDDEN = (
    (re.compile(r"\bwho\b|\bperson\b|\baccount owner\b|\bwho did this\b", re.I), "identity_or_responsibility"),
    (re.compile(r"\b(?:fake|authentic|genuine)\b|\b(?:real or synthetic)\b", re.I), "media_verdict"),
    (re.compile(r"\b(?:intent|motive|guilty|caus(?:e|ed|es|ality))\b", re.I), "intent_or_causation"),
)
_SUPPORTED = re.compile(r"\b(?:connect(?:ed|ion|s)?|link(?:ed|s)?|path(?:s)?|relationship(?:s)?|relate(?:d)?|associated)\b", re.I)
_UNSUPPORTED_SPECIALTY = re.compile(r"\b(?:attachment|parser|parsing|clock\s+offset|timestamp|timezone|transcript|speaker|detector|screening\s+score)\b", re.I)


def plan_context_request(entity_id: Any, question: Any, depth: Any) -> dict[str, Any]:
    entity = str(entity_id or "").strip()
    query = str(question or "").strip()
    if not _ENTITY_ID.fullmatch(entity):
        return {"status": "invalid", "code": "INVALID_ENTITY_ID", "message": "Provide a valid entity ID."}
    if not query or len(query) > 500:
        return {"status": "invalid", "code": "INVALID_CONTEXT_QUERY", "message": "Provide a question of 1–500 characters."}
    if isinstance(depth, bool) or not isinstance(depth, int) or not 1 <= depth <= 3:
        return {"status": "invalid", "code": "INVALID_DEPTH", "message": "Traversal depth must be an integer from 1 to 3."}
    for pattern, reason in _FORBIDDEN:
        if pattern.search(query):
            return {
                "status": "refused", "reason": reason,
                "safeReframe": "I can list source-linked observations and candidate relationships for examiner review.",
            }
    if _UNSUPPORTED_SPECIALTY.search(query):
        return {"status": "unsupported", "reason": "This question needs a parser, clock, transcript, or detector tool that is not configured here."}
    if not _SUPPORTED.search(query):
        return {"status": "unsupported", "reason": "The request is outside the graph path tool's supported scope."}
    return {
        "status": "ready", "agentId": "context-planner", "version": "0.1.0",
        "toolCalls": [{"tool": "graph.explain_entity", "arguments": {"entityId": entity, "depth": depth, "limit": 25}}],
    }
