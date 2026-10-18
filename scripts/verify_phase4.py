"""Live cited report checks using an existing fictional demo summary."""
import hashlib
import json
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
opener = build_opener(ProxyHandler({}))
base = "http://127.0.0.1:8100/api/v1/cases/DF-24-017"
key = "phase4-" + uuid.uuid4().hex
checks = []


def request(path, body=None):
    req = Request(base+path, data=json.dumps(body).encode() if body is not None else None,
                  headers={"Content-Type":"application/json", "Idempotency-Key":key})
    try:
        with opener.open(req, timeout=15) as response:
            raw = response.read()
            return response.status, json.loads(raw) if "application/json" in response.headers.get("Content-Type", "") else raw.decode()
    except HTTPError as exc:
        return exc.code, json.load(exc)


def check(name, condition):
    checks.append({"name":name,"passed":bool(condition)})
    assert condition, name
    print("PASS",name,flush=True)


_, memory = request("/agents/recall?agentId=case-summary&limit=1")
episode_id = memory["data"]["items"][0]["id"]
body = {"title":"Phase 4 demo validation report", "summaryEpisodeId":episode_id}
code, created = request("/reports/from-summary",body)
check("create verified report from saved graph summary",code==200)
ident = created["data"]["id"]
check("idempotent creation replay",request("/reports/from-summary",body)==(code,created))
check("changed request rejected",request("/reports/from-summary",{**body,"title":"different"})[0]==409)
code, saved = request("/reports/"+ident)
check("report snapshot persisted",code==200 and saved["data"]["report"]["summaryEpisodeId"]==episode_id)
_, envelope = request("/reports/"+ident+"/export/json")
digest = hashlib.sha256(json.dumps(envelope["report"],sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()
check("JSON export digest verifies",digest==envelope["contentSha256"])
code, html = request("/reports/"+ident+"/export/html")
check("printable HTML retains draft label and sources",code==200 and "UNREVIEWED DRAFT" in html and "ART-028" in html)
check("unsupported export rejected",request("/reports/"+ident+"/export/pdf")[0]==422)
_, page = request("/pages/reports")
check("saved snapshot appears in Reports read model",any(row.get("id")==ident and row.get("renderable") for row in page["data"]["rows"]))
check("missing report returns 404",request("/reports/RPT-unknown")[0]==404)
ROOT.joinpath("output/phase4-verification.json").write_text(json.dumps({"status":"passed","checks":checks,"reportId":ident,"contentSha256":digest},indent=2),encoding="utf-8")
ROOT.joinpath("output/phase4-demo-report.html").write_text(html,encoding="utf-8")
ROOT.joinpath("output/phase4-demo-report.json").write_text(json.dumps(envelope,indent=2,ensure_ascii=False),encoding="utf-8")
