"""Expose explicit diarization labels as a draft; never infer a person's identity."""
from __future__ import annotations

import re
from typing import Any


def draft_speaker_labels(snapshot: dict[str, Any]) -> dict[str, Any]:
    evidence = snapshot.get("evidence", []) if isinstance(snapshot.get("evidence"), list) else []
    known = {str(item.get("id")) for item in evidence if isinstance(item, dict) and item.get("id")}
    reviews = snapshot.get("reviewItems", []) if isinstance(snapshot.get("reviewItems"), list) else []
    relevant = [item for item in reviews if isinstance(item, dict) and any(term in (str(item.get("type", "")) + " " + str(item.get("title", ""))).casefold() for term in ("speaker", "transcript", "attribution"))]
    review_sources = sorted({source for item in relevant for source in re.findall(r"\bART-[A-Z0-9-]{1,32}\b", str(item.get("evidence", ""))) if source in known})
    segments = snapshot.get("transcriptSegments")
    if not isinstance(segments, list):
        return {"agent": {"id": "transcript-attribution", "version": "0.1.0", "mode": "precise-fail-closed"},
                "state": "unknown", "draftOnly": True, "speakerLabels": [], "sourceIds": review_sources,
                "gap": "No source-linked transcript/diarization segments are attached; no speaker label was generated.",
                "examinerNextStep": "Attach the derived transcript with segment IDs, source spans, and diarization labels, then compare the label to the original media.",
                "limits": ["Speaker labels are not person identities.", "The agent never attributes a statement to an account owner.", "No transcript is generated from audio in this lightweight workflow."]}
    labels = []
    for segment in segments[:2000]:
        if not isinstance(segment, dict):
            continue
        source_id, label = segment.get("sourceId"), segment.get("speakerLabel")
        if source_id not in known or not isinstance(label, str) or not label.strip() or len(label) > 80:
            continue
        labels.append({"segmentId": str(segment.get("segmentId", ""))[:100], "speakerLabel": label.strip(),
                       "start": segment.get("start"), "end": segment.get("end"), "state": "derived", "sourceId": source_id})
    return {"agent": {"id": "transcript-attribution", "version": "0.1.0", "mode": "precise-draft"},
            "state": "derived" if labels else "unknown", "draftOnly": True, "speakerLabels": labels,
            "sourceIds": sorted({item["sourceId"] for item in labels}),
            "gap": None if labels else "No transcript segment met the required case-source and speaker-label schema.",
            "examinerNextStep": "Compare each diarization label against the original source segment before relying on it.",
            "limits": ["Speaker labels are not person identities.", "No identity, account-owner, intent, or guilt attribution is produced."]}
