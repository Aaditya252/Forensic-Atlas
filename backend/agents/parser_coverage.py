"""Report parser coverage only from explicit manifests; never infer completeness."""
from __future__ import annotations

import re
from typing import Any


def _artifact_ids(value: Any, known: set[str]) -> list[str]:
    return sorted(set(re.findall(r"\bART-[A-Z0-9-]{1,32}\b", str(value or ""))) & known)


def inspect_parser_coverage(snapshot: dict[str, Any]) -> dict[str, Any]:
    manifest = snapshot.get("parserManifest")
    evidence = snapshot.get("evidence", []) if isinstance(snapshot.get("evidence"), list) else []
    known = {str(item.get("id")) for item in evidence if isinstance(item, dict) and item.get("id")}
    if not isinstance(manifest, list):
        cues = []
        for item in snapshot.get("reviewItems", []):
            if not isinstance(item, dict) or not any(token in str(item.get("type", "")).casefold() for token in ("parser", "coverage")):
                continue
            cues.append({"reviewId": str(item.get("id", "")), "title": str(item.get("title", ""))[:300],
                         "sourceIds": _artifact_ids(item.get("evidence"), known), "state": "unknown",
                         "gap": "The case has a parser-related review cue, but no parser manifest is attached to verify parsed and referenced record counts."})
        return {"agent": {"id": "parser-coverage", "version": "0.1.0", "mode": "precise"},
                "state": "unknown", "items": cues,
                "gap": "No parser manifest with parsed/reference counts is available; coverage cannot be computed.",
                "limits": ["Missing manifest data does not mean a record is absent.", "No count is inferred from review prose."]}
    items = []
    for row in manifest[:1000]:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("sourceId", ""))
        parsed, referenced = row.get("parsedCount"), row.get("referencedCount")
        valid_counts = (isinstance(parsed, int) and not isinstance(parsed, bool) and parsed >= 0 and
                        isinstance(referenced, int) and not isinstance(referenced, bool) and referenced >= 0)
        items.append({"sourceId": source_id if source_id in known else None,
                      "parsedCount": parsed if valid_counts else None,
                      "referencedCount": referenced if valid_counts else None,
                      "gapCount": max(0, referenced - parsed) if valid_counts else None,
                      "state": "derived" if valid_counts and source_id in known else "unknown",
                      "gap": None if valid_counts and source_id in known else "Manifest row lacks valid counts or a case-known source ID."})
    return {"agent": {"id": "parser-coverage", "version": "0.1.0", "mode": "precise"},
            "state": "derived" if items and all(item["state"] == "derived" for item in items) else "unknown",
            "items": items, "gap": None if items else "Parser manifest is present but has no usable rows.",
            "limits": ["Only explicit manifest counters are compared.", "A parser gap is not proof that the underlying event did not occur."]}
