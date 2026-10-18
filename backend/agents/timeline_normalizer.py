"""Conservative timestamp normalization that never guesses a missing timezone."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any


def normalize_event(event: dict[str, Any], known_source_ids: set[str]) -> dict[str, Any]:
    raw = event.get("timestamp") or event.get("sourceTime") or event.get("time")
    raw_text = str(raw) if raw is not None else ""
    source_text = " ".join(str(event.get(key, "")) for key in ("source", "sourceId", "id"))
    sources = sorted(set(re.findall(r"\bART-[A-Z0-9-]{1,32}\b", source_text)) & known_source_ids)
    if not raw_text:
        return {"eventId": str(event.get("id", "")), "sourceTime": None, "normalizedUtc": None,
                "precision": None, "offsetStatus": "missing_timestamp", "state": "unknown", "sources": sources}
    try:
        parsed = datetime.fromisoformat(raw_text.replace("Z", "+00:00"))
    except ValueError:
        return {"eventId": str(event.get("id", "")), "sourceTime": raw_text, "normalizedUtc": None,
                "precision": None, "offsetStatus": "invalid_timestamp", "state": "unknown", "sources": sources}
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return {"eventId": str(event.get("id", "")), "sourceTime": raw_text, "normalizedUtc": None,
                "precision": None, "offsetStatus": "missing_offset", "state": "unknown", "sources": sources}
    fractional = re.search(r"\.(\d+)", raw_text)
    if fractional and len(fractional.group(1)) > 6:
        return {"eventId": str(event.get("id", "")), "sourceTime": raw_text, "normalizedUtc": None,
                "precision": f"fractional-second ({len(fractional.group(1))} digits)",
                "offsetStatus": "precision_not_supported", "state": "unknown", "sources": sources}
    precision = f"fractional-second ({len(fractional.group(1))} digits)" if fractional else "second"
    utc_time = parsed.astimezone(timezone.utc)
    utc_value = utc_time.strftime("%Y-%m-%dT%H:%M:%S")
    if fractional:
        digits = len(fractional.group(1))
        utc_value += "." + f"{utc_time.microsecond:06d}"[:digits]
    utc_value += "Z"
    return {"eventId": str(event.get("id", "")), "sourceTime": raw_text, "normalizedUtc": utc_value,
            "precision": precision, "offsetStatus": "explicit_offset", "state": "derived", "sources": sources}


def normalize_timeline(events: Any, known_source_ids: set[str]) -> dict[str, Any]:
    rows = events if isinstance(events, list) else []
    return {"agent": {"id": "timeline-normalizer", "version": "0.1.0", "mode": "precise"},
            "items": [normalize_event(row, known_source_ids) for row in rows if isinstance(row, dict)],
            "limits": ["Original timestamp text is retained.", "Timezone is never inferred from workstation or case locale.",
                       "Reported precision is the text precision supplied by the source field, not clock accuracy."]}
