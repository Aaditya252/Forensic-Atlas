"""Exercise the running local summary API using the fictional demo case."""
import json
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
opener = build_opener(ProxyHandler({}))
base = "http://127.0.0.1:8100/api/v1/cases/DF-24-017/summary"
key = "phase2-verification-" + uuid.uuid4().hex


def request(body=None):
    req = Request(base, data=json.dumps(body).encode() if body is not None else None,
                  headers={"Content-Type": "application/json", "Idempotency-Key": key})
    try:
        with opener.open(req, timeout=120) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.load(exc)


checks = []


def check(name, condition):
    checks.append({"name": name, "passed": bool(condition)})
    assert condition, name
    print("PASS", name, flush=True)


status, first = request({})
check("real model API generation", status == 200 and first["data"]["verification"]["ok"])
result = first["data"]
check("graph and unresolved review coverage", {"graph-path", "review-record"} <= {row["origin"] for row in result["statements"]})
check("model provenance retained", bool(result["model"]["modelSha256"]) and result["model"]["trainedByUs"] is False)
check("idempotent replay", request({}) == (status, first))
check("request mismatch rejected", request({"entityId": "SES-0942"})[0] == 409)
code, latest = request()
check("draft persisted in graph memory", code == 200 and latest["data"]["latestSummary"]["summaryId"] == result["summaryId"])
check("draft retains exact context statements", all(row in result["inputContext"]["facts"] for row in result["statements"]))
(ROOT/"output"/"phase2-verification.json").write_text(json.dumps({"status":"passed", "checks":checks, "summaryId":result["summaryId"], "elapsedMs":result["elapsedMs"], "usage":result["usage"], "model":result["model"]}, indent=2), encoding="utf-8")
