"""Case-scoped, tool-grounded hybrid forensic agent workflow.

The current implementation combines deterministic specialist agents over the
case read model. It deliberately does not call an LLM or media detector: those
providers are not configured in this development workspace.
"""
from __future__ import annotations

from typing import Any


AGENT_ROSTER = [
    {"id": "case-orchestrator", "name": "Case orchestrator", "domain": "Cross-layer", "mode": "Hybrid", "status": "enabled", "description": "Coordinates scoped case, graph, media, and research tools into a cited examiner brief."},
    {"id": "case-summary", "name": "Cited case summary", "domain": "Evidence summary", "mode": "Local LLM + exact-source verifier", "status": "conditional", "description": "A small local model selects and orders verified fact cards for an extractive, source-cited examiner draft."},
    {"id": "graph-context", "name": "Graph context agent", "domain": "FalkorDB graph", "mode": "Tool + rules", "status": "conditional", "description": "Finds bounded, source-linked entity paths; never writes generated Cypher."},
    {"id": "timeline-correlation", "name": "Timeline correlation agent", "domain": "Timeline", "mode": "Rules + review context", "status": "enabled", "description": "Surfaces candidate temporal relationships and competing explanations."},
    {"id": "timeline-normalizer", "name": "Timeline normalizer", "domain": "Timeline", "mode": "Precise", "status": "enabled", "description": "Converts timestamps only when an explicit timezone offset is present; preserves raw source time."},
    {"id": "review-triage", "name": "Review triage", "domain": "Examiner review", "mode": "Precise", "status": "enabled", "description": "Suggests an explainable review sequence from source dependencies without changing decisions."},
    {"id": "parser-coverage", "name": "Parser coverage", "domain": "Source coverage", "mode": "Precise", "status": "conditional", "description": "Computes only from an explicit parser manifest; otherwise reports the missing measurement."},
    {"id": "transcript-attribution", "name": "Transcript speaker labels", "domain": "Media / review", "mode": "Precise draft", "status": "conditional", "description": "Surfaces supplied diarization labels for review; never identifies a person."},
    {"id": "media-metadata", "name": "Media metadata context", "domain": "Media / integrity", "mode": "Saved inspections + source verifier", "status": "conditional", "description": "Connects historical uploaded-file inspections to case synthesis and cited summaries without authenticity inference."},
    {"id": "media-forensics", "name": "Media forensics agent", "domain": "Deepfake / multimedia", "mode": "Detector-gated", "status": "blocked", "description": "Summarizes only persisted, validated detector output; this workspace has no validated model."},
    {"id": "integrity-coverage", "name": "Integrity & coverage agent", "domain": "Evidence intake", "mode": "Precise", "status": "enabled", "description": "Maps registered evidence, partial states, and source coverage gaps."},
    {"id": "research-mapper", "name": "Forensic research mapper", "domain": "Research", "mode": "Curated sources", "status": "enabled", "description": "Maps examiner questions to authoritative evaluation and preservation guidance."},
    {"id": "impact-assessment", "name": "Impact assessment agent", "domain": "Cross-layer", "mode": "Rules + provenance", "status": "enabled", "description": "Explains how known gaps could affect interpretation, with alternatives and limits."},
    {"id": "case-memory", "name": "Case memory & handoffs", "domain": "Cross-layer", "mode": "FalkorDB + rules", "status": "enabled", "description": "Persists case-scoped episodes and versioned work handoffs with source trails."},
]

RESEARCH = [
    {"id": "NIST-GFE", "title": "Guardians of Forensic Evidence", "organization": "NIST", "url": "https://www.nist.gov/programs-projects/guardians-forensic-evidence", "use": "Deepfake evaluation design, robustness, generalization, and transition from lab benchmarks to forensic workflows."},
    {"id": "NISTIR-8387", "title": "Digital Evidence Preservation: Considerations for Evidence Handlers", "organization": "NIST", "url": "https://www.nist.gov/publications/digital-evidence-preservation-considerations-evidence-handlers", "use": "Preservation, evidence handling, and keeping source media distinct from derived analysis."},
    {"id": "NIST-AIRM-1", "title": "AI Risk Management Framework", "organization": "NIST", "url": "https://www.nist.gov/itl/ai-risk-management-framework", "use": "Documenting AI risks, evaluation, monitoring, limitations, and human review across the lifecycle."},
    {"id": "CELEB-DF", "title": "Celeb-DF: A Large-scale Challenging Dataset for DeepFake Forensics", "organization": "CVPR 2020", "url": "https://openaccess.thecvf.com/content_CVPR_2020/papers/Li_Celeb-DF_A_Large-Scale_Challenging_Dataset_for_DeepFake_Forensics_CVPR_2020_paper.pdf", "use": "Include as one benchmark in training/evaluation; report its domain separately and do not treat benchmark performance as field reliability."},
    {"id": "FACE-FORENSICS-PLUS", "title": "FaceForensics++: Learning to Detect Manipulated Facial Images", "organization": "ICCV 2019", "url": "https://openaccess.thecvf.com/content_ICCV_2019/papers/Rossler_FaceForensics_Learning_to_Detect_Manipulated_Facial_Images_ICCV_2019_paper.pdf", "use": "Compare against multiple manipulation methods and compression conditions; use held-out methods to probe generalization."},
    {"id": "DEEPER-FORENSICS", "title": "DeeperForensics-1.0: A Large-Scale Dataset for Real-World Face Forgery Detection", "organization": "CVPR 2020", "url": "https://openaccess.thecvf.com/content_CVPR_2020/papers/Jiang_DeeperForensics-1.0_A_Large-Scale_Dataset_for_Real-World_Face_Forgery_Detection_CVPR_2020_paper.pdf", "use": "Evaluate realistic perturbations and robustness beyond clean benchmark clips."},
]


def _ids(value: Any, known: set[str]) -> list[str]:
    if not isinstance(value, str):
        return []
    import re
    return sorted(set(re.findall(r"\bART-[A-Z0-9-]+\b", value)) & known)


def build_case_brief(snapshot: dict[str, Any], *, graph_available: bool, graph_entities: list[dict[str, Any]] | None = None,
                     detector_configured: bool = False) -> dict[str, Any]:
    evidence = snapshot.get("evidence", []) if isinstance(snapshot.get("evidence"), list) else []
    reviews = snapshot.get("reviewItems", []) if isinstance(snapshot.get("reviewItems"), list) else []
    coverage = snapshot.get("sourceCoverage", []) if isinstance(snapshot.get("sourceCoverage"), list) else []
    known = {str(row.get("id")) for row in evidence if isinstance(row, dict) and row.get("id")}
    partial = [row for row in evidence if isinstance(row, dict) and str(row.get("status", "")).lower() in {"partial", "review"}]
    review_sources = sorted({source for row in reviews if isinstance(row, dict) for source in _ids(row.get("evidence"), known)})
    open_gaps = [row for row in coverage if isinstance(row, dict) and str(row.get("state", "")).lower() not in {"complete", "covered"}]
    overview_count = int(snapshot.get("overview", {}).get("evidenceItems", len(evidence)))
    media = [row for row in evidence if isinstance(row, dict) and any(term in str(row.get("type", "")).lower() for term in ("video", "audio", "image", "media"))]
    correlation = [row for row in reviews if isinstance(row, dict) and any(term in (str(row.get("type", "")) + " " + str(row.get("title", ""))).lower() for term in ("correlation", "timeline", "clock"))]
    correlation_ids = sorted({source for row in correlation for source in _ids(row.get("evidence"), known)})
    graph_entities = graph_entities or []

    workstreams = [
        {
            "agentId": "integrity-coverage", "name": "Evidence integrity & source coverage", "state": "derived" if evidence else "unknown",
            "summary": f"{len(evidence)} artifact detail rows are available in this snapshot (the overview lists {overview_count} evidence items); {len(partial)} detail rows carry partial or review status.",
            "sources": sorted(str(row["id"]) for row in evidence if row.get("id") in known),
            "impact": "Partial acquisition or parsing can change what can be compared across sources; an unparsed or unavailable item is a gap, not proof that an event did not occur.",
            "nextStep": "Resolve source coverage and parser gaps, then preserve each source-to-derived-record link.",
        },
        {
            "agentId": "timeline-correlation", "name": "Timeline & candidate correlation", "state": "hypothesis" if correlation else "unknown",
            "summary": (f"{len(correlation)} open timeline/correlation review item(s) reference case artifacts. Temporal alignment is a candidate association only." if correlation else "No supported timeline correlation was returned from the current review read model."),
            "sources": correlation_ids,
            "impact": "Unknown clock offsets, incomplete logs, or delayed collection can change event ordering and weaken or strengthen a candidate relationship.",
            "alternatives": ["Independent events may be close in time.", "Clock skew or collection delay may explain apparent ordering."],
            "nextStep": "Validate source clock offsets and compare independent records before promoting any link.",
        },
        {
            "agentId": "graph-context", "name": "Graph context", "state": "derived" if graph_available else "unknown",
            "summary": (f"FalkorDB is available with {len(graph_entities)} case-projection entities. Use the bounded path tool for source-linked paths." if graph_available else "FalkorDB is not connected; no relationship paths were inferred from the browser or case text."),
            "sources": sorted({str(row.get("source")) for row in graph_entities if row.get("source") in known}),
            "impact": "A graph path can make cross-source relationships easier to inspect, but its stored edges retain their evidence state and do not establish identity, intent, or causation.",
            "nextStep": "Connect FalkorDB and verify graph projection provenance before asking the graph-context agent to trace a path." if not graph_available else "Trace relevant paths from a selected entity and inspect every source artifact.",
        },
        {
            "agentId": "media-forensics", "name": "Deepfake & multimedia forensics", "state": "unknown" if not detector_configured else "derived",
            "summary": (f"{len(media)} media artifact(s) are registered. No validated detector is configured, so no model score or authenticity claim is available." if not detector_configured else f"{len(media)} media artifact(s) are registered; review persisted detector runs before interpreting cues."),
            "sources": sorted(str(row["id"]) for row in media if row.get("id") in known),
            "impact": "Compression, short duration, edits, and domain shift can alter detector behavior; a screening cue must not substitute for media examination.",
            "nextStep": "Preserve and hash originals; use a validated, versioned model with cross-dataset evaluation and localized cues before examiner review.",
        },
        {
            "agentId": "impact-assessment", "name": "Impact & alternative explanations", "state": "derived" if reviews else "unknown",
            "summary": f"{len(reviews)} open review item(s) remain in the case read model; {len(review_sources)} distinct artifact IDs are referenced.",
            "sources": review_sources,
            "impact": "Unresolved attribution, parser, clock, or media uncertainty can change the interpretation and confidence of a proposed event narrative.",
            "alternatives": ["Missing source material may explain an apparent mismatch.", "A shared device, shared account, edit, or clock variance may create a relationship without establishing who acted or why."],
            "nextStep": "Resolve the highest-impact review dependencies and keep hypotheses separate from examiner findings.",
        },
    ]
    return {
        "schemaVersion": 1,
        "runId": "run-pending",
        "caseId": snapshot.get("case", {}).get("id"),
        "mode": "hybrid-tool-grounded",
        "createdAt": None,
        "provider": {"llm": "not-invoked", "mediaDetector": "configured" if detector_configured else "not-configured", "graph": "connected" if graph_available else "not-connected"},
        "headline": "Cross-layer examiner brief ready" if evidence else "No case evidence available",
        "workstreams": workstreams,
        "priorities": [row["nextStep"] for row in workstreams[:4]],
        "research": RESEARCH,
        "openReviewCount": len(reviews),
        "evidenceCount": len(evidence),
        "evidenceOverviewCount": overview_count,
        "limits": [
            "This coordination run uses deterministic specialists over the case read model. The cited case summary is an explicit local-model action; media screening requires a validated detector.",
            "Cause and impact are framed as candidate mechanisms and possible effects, not findings. Alternative explanations remain open.",
            "Evidence text is treated as data. Agents cannot identify a person, infer intent, decide guilt, or make authenticity findings.",
        ],
    }
