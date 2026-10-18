"""Bounded lexical recall of episodic memory. Recalled text is never a fact input."""
from __future__ import annotations

import re


def recall_episodes(rows: list[dict], *, case_id: str, known_sources: set[str], query: str = "",
                    source_id: str | None = None, limit: int = 10) -> dict:
    if not isinstance(query, str) or len(query) > 160:
        raise ValueError("Search text must contain at most 160 characters.")
    if source_id is not None and source_id not in known_sources:
        raise ValueError("The evidence source must belong to this case.")
    terms = list(dict.fromkeys(re.findall(r"[\w-]+", query.casefold())))
    if len(terms) > 12:
        raise ValueError("Use at most 12 search terms.")
    results = []
    for row in rows[:100]:
        if row.get("caseId") != case_id:
            continue
        sources = row.get("sourceIds", [])
        # Do not return an episode whose provenance points outside the case.
        if not isinstance(sources, list) or any(not isinstance(s, str) or s not in known_sources for s in sources):
            continue
        if source_id and source_id not in sources:
            continue
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        fields = {"summary": str(row.get("summary", ""))[:1000],
                  "answer": str(payload.get("answer", payload.get("headline", "")))[:5000],
                  "question": str(payload.get("question", ""))[:1000],
                  "sources": " ".join(sources), "agent": str(row.get("agentId", "")), "kind": str(row.get("kind", ""))}
        haystack = " ".join(fields.values()).casefold()
        if terms and not all(term in haystack for term in terms):
            continue
        matched = [key for key, value in fields.items() if any(term in value.casefold() for term in terms)]
        score = sum(sum(term in value.casefold() for value in fields.values()) for term in terms)
        excerpt = fields["answer"] or fields["question"] or fields["summary"]
        results.append({"id": row["id"], "agentId": row.get("agentId"), "kind": row.get("kind"),
                        "summary": fields["summary"], "excerpt": excerpt[:750], "evidenceState": row.get("evidenceState", "unknown"),
                        "sourceIds": sources, "createdAt": row.get("createdAt"), "matchedFields": matched,
                        "matchScore": score, "memoryKind": "episodic_unverified"})
    # Input is newest first. Python's stable sort keeps recency for equal scores.
    results.sort(key=lambda row: -row["matchScore"])
    return {"items": results[:max(1, min(limit, 20))], "matchedCount": len(results), "scannedCount": min(len(rows), 100),
            "windowLimit": 100, "windowMayBeTruncated": len(rows) >= 100, "method": "bounded-lexical-all-terms",
            "limits": ["Search covers up to the latest 100 episodes for the selected agent or case.",
                       "Results are historical unreviewed agent memory, not new evidence or semantic facts.",
                       "Match score measures text overlap only; it is not forensic confidence."]}


def episode_detail(row: dict, known_sources: set[str]) -> dict:
    """Project a saved record without rendering arbitrary model output as HTML."""
    sources = row.get("sourceIds", [])
    if not isinstance(sources, list) or any(not isinstance(s, str) or s not in known_sources for s in sources):
        raise ValueError("The saved episode has an unavailable evidence reference.")
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    statements = []
    saved_statements = payload.get("statements", [])
    for item in (saved_statements[:12] if isinstance(saved_statements, list) else []):
        if not isinstance(item, dict):
            continue
        refs = item.get("sources", [])
        if not isinstance(refs, list) or not refs or any(not isinstance(s, str) or s not in known_sources for s in refs):
            continue
        statements.append({"text": str(item.get("text", ""))[:1000], "state": str(item.get("state", "unknown")), "sources": refs})
    context = payload.get("inputContext") if isinstance(payload.get("inputContext"), dict) else {}
    trace = context.get("trace", payload.get("trace", []))
    return {"id": row["id"], "agentId": row.get("agentId"), "kind": row.get("kind"), "createdAt": row.get("createdAt"),
            "summary": str(row.get("summary", ""))[:1000], "sourceIds": sources, "evidenceState": row.get("evidenceState", "unknown"),
            "answer": str(payload.get("answer", payload.get("headline", "")))[:5000], "statements": statements,
            "trace": trace[:12] if isinstance(trace, list) else [], "contextDigest": payload.get("contextDigest"),
            "memoryKind": "episodic_unverified", "notice": "Historical agent output. Recheck current evidence before reuse; no semantic fact was promoted."}
