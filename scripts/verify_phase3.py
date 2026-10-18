"""Read-only live recall checks against the fictional local demo case."""
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, build_opener

opener = build_opener(ProxyHandler({}))
base = "http://127.0.0.1:8100/api/v1/cases/DF-24-017/agents/recall"
checks = []


def read(suffix=""):
    try:
        with opener.open(base+suffix, timeout=10) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.load(exc)


def check(name, condition):
    checks.append({"name":name, "passed":bool(condition)})
    assert condition, name
    print("PASS", name, flush=True)


code, response = read("?agentId=case-summary&sourceId=ART-028&q=ART-028&limit=2")
items = response.get("data", {}).get("items", [])
check("saved model summaries are searchable", code == 200 and bool(items))
check("agent and source filters", all(i["agentId"] == "case-summary" and "ART-028" in i["sourceIds"] for i in items))
check("bounded window and result limit", response["data"]["scannedCount"] <= 100 and len(items) <= 2)
code, detail = read("/"+items[0]["id"])
check("direct episode lookup retains source trail", code == 200 and detail["data"]["sourceIds"] == items[0]["sourceIds"])
check("saved graph tool trace is available", any(t["tool"] == "graph.explain_entity" for t in detail["data"]["trace"]))
check("recall is explicitly unreviewed", detail["data"]["memoryKind"] == "episodic_unverified")
check("unknown source rejected", read("?sourceId=ART-NOT-IN-CASE")[0] == 422)
check("missing episode returns 404", read("/EP-NOT-PRESENT")[0] == 404)
check("empty search result has no substitute data", read("?q=nonexistentuniquerecalltoken")[1]["data"]["items"] == [])
check("oversized limit rejected", read("?limit=21")[0] == 422)
Path(__file__).resolve().parents[1].joinpath("output/phase3-verification.json").write_text(json.dumps({"status":"passed", "checks":checks, "episodeId":items[0]["id"]},indent=2),encoding="utf-8")
