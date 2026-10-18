"""Deterministic report snapshots from exact-source case summaries."""
from __future__ import annotations

import hashlib
import json
from html import escape

from .agent_prompts import verify_output


def content_digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def build_report(snapshot: dict, episode: dict, *, report_id: str, title: str, created_at: str) -> dict:
    case_id = snapshot["case"]["id"]
    payload = episode.get("payload", {})
    if (episode.get("caseId") != case_id or episode.get("agentId") != "case-summary" or
            not isinstance(payload, dict) or payload.get("caseId") != case_id or payload.get("method") != "llm-ranked-extractive"):
        raise ValueError("Choose a cited case-summary episode from the selected case.")
    context = payload.get("inputContext", {})
    expected_digest = hashlib.sha256(json.dumps(context, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if payload.get("contextDigest") != expected_digest:
        raise ValueError("The saved summary context digest does not match its content.")
    cards = context.get("facts", [])
    statements = payload.get("statements", [])
    if (not isinstance(cards, list) or not isinstance(statements, list) or not 1 <= len(statements) <= 6 or
            any(not isinstance(s, dict) or s not in cards for s in statements)):
        raise ValueError("The summary statements do not match its saved fact cards.")
    if len({s.get("factId") for s in statements}) != len(statements):
        raise ValueError("The saved summary repeats a fact ID.")
    known = {e["id"] for e in snapshot["evidence"]}
    if not verify_output(payload, known)["ok"]:
        raise ValueError("The summary failed citation and evidence-state verification.")
    sources = sorted({source for statement in statements for source in statement["sources"]})
    if set(payload.get("sources", [])) != set(sources):
        raise ValueError("The summary source list does not match its statements.")
    content = {"schemaVersion": 1, "reportId": report_id, "caseId": case_id, "caseTitle": snapshot["case"]["title"],
               "title": title, "createdAt": created_at, "status": "unreviewed_draft", "summaryEpisodeId": episode["id"],
               "summaryId": payload.get("summaryId"), "summaryCreatedAt": payload.get("createdAt"),
               "statements": statements, "sources": sources,
               "sourceRegister": [{key: row.get(key) for key in ("id", "name", "type", "sha256")}
                                  for row in snapshot["evidence"] if row["id"] in sources],
               "model": payload.get("model", {}), "contextDigest": payload["contextDigest"],
               "toolTrace": context.get("trace", []),
               "verification": {"ok": True, "method": "exact saved fact cards, context digest, case source and evidence-state checks"},
               "limitations": ["Unreviewed draft copied from a historical summary; statements have not been refreshed against later case changes.",
                               "The workflow examines case metadata and graph records, not original evidence bytes.",
                               "Citations and hashes do not establish source accuracy, authenticity, identity, intent, or causation.",
                               "This report is not signed, certified, or approved by an examiner. Local development data may be fictional."]}
    # JSON round-trip detaches the immutable snapshot from mutable caller dictionaries.
    content = json.loads(json.dumps(content, ensure_ascii=False))
    return {"report": content, "digestAlgorithm": "SHA-256", "contentSha256": content_digest(content)}


def render_html(envelope: dict) -> str:
    report = envelope["report"]
    text = lambda value: escape(str(value if value is not None else "Not recorded"))
    rows = "".join(f'<tr><td>{text(s["state"])}</td><td>{text(s["text"])}</td><td>{text(", ".join(s["sources"]))}</td></tr>' for s in report["statements"])
    sources = "".join(f'<tr><td>{text(s["id"])}</td><td>{text(s["name"])}</td><td>{text(s["type"])}</td><td>{text(s.get("sha256"))}</td></tr>' for s in report["sourceRegister"])
    limits = "".join(f'<li>{text(item)}</li>' for item in report["limitations"])
    provenance = text(json.dumps({key:report[key] for key in ("summaryId", "summaryEpisodeId", "summaryCreatedAt", "model", "contextDigest", "toolTrace")}, indent=2, ensure_ascii=False))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{text(report["title"])} · Forensic Atlas</title>
<style>body{{margin:0;background:#e9edf0;color:#243344;font:15px/1.65 system-ui,sans-serif}}main{{max-width:1000px;margin:32px auto;padding:48px;background:white;border-radius:12px}}header{{border-bottom:3px solid #16877e;padding-bottom:24px}}.eyebrow{{color:#16766e;font-size:12px;letter-spacing:2px;font-weight:700}}h1{{font-size:32px;line-height:1.2}}h2{{font-size:20px;margin-top:32px}}.notice{{padding:16px;border:1px solid #dfc38c;background:#fff8e9;border-radius:8px}}table{{width:100%;border-collapse:collapse;font-size:13px;table-layout:fixed}}th,td{{padding:12px;border-bottom:1px solid #dce2e6;text-align:left;vertical-align:top;overflow-wrap:anywhere}}th{{background:#eef5f4}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;padding:18px;background:#f1f4f6;font-size:11px}}small{{color:#5c6b78}}.digest{{overflow-wrap:anywhere;font:12px/1.7 monospace}}@media(max-width:700px){{main{{margin:0;padding:22px;border-radius:0}}h1{{font-size:25px}}th,td{{padding:7px}}}}@media print{{body{{background:white}}main{{margin:0;padding:0;border-radius:0}}@page{{size:A4;margin:18mm}}h2{{break-after:avoid}}tr{{break-inside:avoid}}pre{{font-size:9px}}}}</style></head><body><main><header><div class="eyebrow">FORENSIC ATLAS / CASE REPORT</div><h1>{text(report["title"])}</h1><p>{text(report["caseId"])} · {text(report["caseTitle"])}</p><small>{text(report["reportId"])} · Created {text(report["createdAt"])}</small></header>
<p class="notice"><strong>UNREVIEWED DRAFT</strong> · Historical source-linked summary. Examiner approval has not been recorded.</p><h2>Evidence-linked statements</h2><table><thead><tr><th style="width:14%">State</th><th style="width:64%">Saved statement</th><th>Sources</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Source register</h2><table><thead><tr><th>ID</th><th>Artifact</th><th>Type</th><th>SHA-256 if recorded</th></tr></thead><tbody>{sources}</tbody></table><h2>Method and limitations</h2><ul>{limits}</ul><h2>Model and tool provenance</h2><pre>{provenance}</pre><h2>Snapshot integrity</h2><p class="digest">Canonical JSON content SHA-256: {text(envelope["contentSha256"])}</p><small>The digest covers the report object in the JSON export, serialized as UTF-8 with sorted keys, no ASCII escaping, and compact separators. It does not cover this HTML file and is not a digital signature.</small></main></body></html>'''
