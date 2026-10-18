"""Evidence-only narration over validated FalkorDB tool results."""
from __future__ import annotations

import re
from typing import Any

_INSTRUCTION_LIKE = re.compile(
    r"\b(ignore\s+(?:all\s+)?(?:previous|prior|system)|reveal\s+(?:the\s+)?(?:secret|prompt)|"
    r"disregard\s+(?:all\s+)?instructions|you\s+are\s+now\s+(?:an?\s+)?(?:system|assistant)|"
    r"execute\s+this\s+command)\b", re.I,
)


def _path_sources(path: dict[str, Any]) -> set[str]:
    sources = {str(node.get("source")) for node in path.get("nodes", []) if node.get("source")}
    sources.update(str(link.get("artifactId")) for link in path.get("links", []) if link.get("artifactId"))
    return sources


def narrate_paths(entity_id: str, paths: list[dict[str, Any]], known_source_ids: set[str]) -> dict[str, Any]:
    safe_paths: list[dict[str, Any]] = []
    statements: list[dict[str, Any]] = []
    observed_notes: list[dict[str, Any]] = []
    all_sources: set[str] = set()
    for path in paths[:25]:
        if not isinstance(path, dict):
            continue
        sources = sorted(_path_sources(path) & known_source_ids)
        if not sources or _path_sources(path) - known_source_ids:
            continue
        all_sources.update(sources)
        nodes, links = [], []
        injection_sources: set[str] = set()
        for node in path.get("nodes", []):
            item = {key: node.get(key) for key in ("id", "label", "name", "source", "claim") if node.get(key) is not None}
            if _INSTRUCTION_LIKE.search(str(item.get("name", ""))):
                item["name"] = "[instruction-like evidence text omitted]"
                if node.get("source") in known_source_ids:
                    injection_sources.add(str(node["source"]))
            nodes.append(item)
        for link in path.get("links", []):
            item = {key: link.get(key) for key in ("type", "state", "artifactId") if link.get(key) is not None}
            links.append(item)
        clean_path = {"nodes": nodes, "links": links, "sources": sources}
        safe_paths.append(clean_path)
        states = {str(link.get("state", "unknown")) for link in links}
        state = "candidate" if "candidate" in states else "observed" if states and states <= {"observed"} else "derived"
        relation_names = sorted({str(link.get("type", "relationship")) for link in links})
        statement_text = f"FalkorDB returned a source-linked path from {entity_id} with relationship types {', '.join(relation_names) or 'unspecified'}; sources: {', '.join(sources)}."
        statements.append({"text": statement_text, "state": state, "sources": sources})
        if injection_sources:
            observed_notes.append({
                "text": "Instruction-like text was present in graph evidence content and treated as observed data, not an instruction; text omitted from narration. Sources: " + ", ".join(sorted(injection_sources)) + ".",
                "state": "observed", "sources": sorted(injection_sources),
            })
    if not statements:
        return {
            "answer": "No source-linked path was returned by the bounded traversal.",
            "state": "unknown", "sources": [], "statements": [], "observedNotes": observed_notes,
            "gap": {"state": "unknown", "message": "The bounded graph query returned no verifiable source-linked path; this result cannot establish whether a relationship is present."},
            "paths": [],
        }
    statements.extend(observed_notes)
    answer = statements[0]["text"] if len(statements) == 1 else f"FalkorDB returned {len(safe_paths)} source-linked path(s); each remains subject to examiner review. Sources: {', '.join(sorted(all_sources))}."
    state = "candidate" if any(item["state"] == "candidate" for item in statements) else "observed"
    return {"answer": answer, "state": state, "sources": sorted(all_sources), "statements": statements, "observedNotes": observed_notes, "gap": None, "paths": safe_paths}
