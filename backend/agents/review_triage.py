"""Rule-based review ordering. This agent suggests attention order; it never decides."""
from __future__ import annotations

import re
from typing import Any


_RULES = (
    ("source-dependency", ("parser", "attachment", "unparsed", "payload", "coverage"),
     "Resolve source availability and parsing gaps before relying on downstream comparisons.",
     "Check the referenced source payload and parser coverage; record any unavailable material as a gap."),
    ("clock-quality", ("clock", "offset", "timestamp", "time offset"),
     "Clarify timestamp offset and precision before comparing event order.",
     "Verify the source clock offset and preserve original timestamp precision before temporal analysis."),
    ("attribution-review", ("attribution", "speaker", "transcript"),
     "Review the cited media span and keep speaker labels separate from person identity.",
     "Inspect the cited source segment and document uncertainty; a speaker label does not identify a person."),
    ("candidate-link", ("correlation", "close in time", "candidate link"),
     "Check source clock quality and independent records before assessing a temporal association.",
     "Compare independent records and clock quality; temporal proximity alone does not establish causation."),
    ("media-screening", ("media", "detector", "deepfake", "authenticity"),
     "Review the original and screening limitations; a detector cue is not an authenticity finding.",
     "Inspect the preserved source and model/run limitations; do not infer an authentic or manipulated verdict."),
)


def _source_ids(text: str, known: set[str]) -> list[str]:
    return sorted(set(re.findall(r"\bART-[A-Z0-9-]{1,32}\b", text)) & known)


def triage_reviews(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return stable, explainable ordering from existing review metadata only."""
    evidence = snapshot.get("evidence", []) if isinstance(snapshot.get("evidence"), list) else []
    reviews = snapshot.get("reviewItems", []) if isinstance(snapshot.get("reviewItems"), list) else []
    known = {str(row.get("id")) for row in evidence if isinstance(row, dict) and row.get("id")}
    candidates = []
    for row in reviews:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        # Triage category comes from typed metadata only; narrative text cannot
        # steer workflow routing or act as an instruction.
        text = " ".join(str(row.get(key, "")) for key in ("type", "title")).casefold()
        rule = next((item for item in _RULES if any(term in text for term in item[1])), None)
        if rule:
            category, _, rationale, next_step = rule
            rank = next(i for i, item in enumerate(_RULES) if item is rule)
        else:
            category, rationale, next_step, rank = "general-review", "No dependency category matched; retain the item's existing examiner review status.", "Inspect the claim and its cited source material.", len(_RULES)
        raw_reference = str(row.get("evidence", ""))
        sources = _source_ids(raw_reference, known)
        candidates.append({"reviewId": str(row["id"]), "title": str(row.get("title", "Review item"))[:300],
                           "category": category, "priorityOrder": rank + 1, "state": "derived",
                           "rationale": rationale, "nextStep": next_step, "sourceIds": sources})
    candidates.sort(key=lambda item: (item["priorityOrder"], item["reviewId"]))
    for index, item in enumerate(candidates, start=1):
        item["rank"] = index
    return {"agent": {"id": "review-triage", "version": "0.1.0", "mode": "precise"},
            "method": "fixed dependency categories; no model score or examiner decision used",
            "orderedItems": candidates,
            "limits": ["Ordering is an attention aid, not a review decision.",
                       "Priority follows visible item type/title text and does not establish factual importance.",
                       "Only case-known artifact IDs are returned as sources."]}
