"""Download small, revision-pinned memory benchmarks for evaluation only.

Uses only the standard library. Never loads benchmark data into case databases.
"""
from __future__ import annotations

import hashlib
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "datasets" / "evaluation"
MAX_FILE_BYTES = 64 * 1024 * 1024


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "ForensicAtlas-EvalDatasetSetup/1.0"})
    with urlopen(request, timeout=90) as response:
        chunks, size = [], 0
        while True:
            chunk = response.read(256 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise ValueError("Download exceeded the 64 MiB per-file limit.")
            chunks.append(chunk)
        data = b"".join(chunks)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("Download exceeded the 64 MiB per-file limit.")
    return data


def metadata(url: str) -> dict:
    return json.loads(fetch(url))


def save(folder: Path, filename: str, content: bytes, source: str) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    path.write_bytes(content)
    return {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "url": source,
            "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=["longmemeval-oracle", "locomo"])
    args = parser.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    entries = [json.loads(path.read_text(encoding="utf-8")) for path in DEST.glob("*/provenance.json")]
    recipes = [
        {"id": "longmemeval-oracle", "hf": "xiaowu0162/longmemeval-cleaned",
         "repo": "xiaowu0162/LongMemEval", "file": "longmemeval_oracle.json",
         "license_file": "LICENSE", "license": "MIT", "required": {"question_id", "question", "haystack_sessions"},
         "use": "Evaluation only. Oracle supplies evidence sessions: it does not evaluate full-history retrieval."},
        {"id": "locomo", "repo": "snap-research/locomo", "file": "data/locomo10.json",
         "license_file": "LICENSE.txt", "license": "CC-BY-NC-4.0", "required": {"sample_id", "conversation", "qa"},
         "use": "Noncommercial research evaluation only. Excluded from training and commercial product data. Image URLs are not downloaded."},
    ]
    for recipe in recipes:
        if args.only and args.only != recipe["id"]:
            continue
        folder = DEST / recipe["id"]
        repo_revision = metadata(f"https://api.github.com/repos/{recipe['repo']}/commits/main")["sha"]
        raw_base = f"https://raw.githubusercontent.com/{recipe['repo']}/{repo_revision}"
        license_url = f"{raw_base}/{recipe['license_file']}"
        license_bytes = fetch(license_url)
        license_text = license_bytes.decode("utf-8")
        marker = "Permission is hereby granted" if recipe["license"] == "MIT" else "Attribution-NonCommercial 4.0"
        if marker not in license_text:
            raise ValueError(f"License check failed for {recipe['id']}; review upstream terms.")
        if recipe.get("hf"):
            info = metadata(f"https://huggingface.co/api/datasets/{recipe['hf']}")
            revision = info["sha"]
            data_url = f"https://huggingface.co/datasets/{recipe['hf']}/resolve/{revision}/{recipe['file']}"
            card_url = f"https://huggingface.co/datasets/{recipe['hf']}/resolve/{revision}/README.md"
        else:
            revision = repo_revision
            data_url = f"{raw_base}/{recipe['file']}"
            card_url = f"{raw_base}/README.MD"
        print(f"Downloading {recipe['id']} from pinned revision {revision[:12]}...", flush=True)
        raw = fetch(data_url)
        records = json.loads(raw)
        if not isinstance(records, list) or not records or any(not isinstance(row, dict) or not recipe["required"].issubset(row) for row in records):
            raise ValueError(f"Unexpected record schema for {recipe['id']}.")
        files = [save(folder, Path(recipe["file"]).name, raw, data_url),
                 save(folder, recipe["license_file"], license_bytes, license_url),
                 save(folder, "UPSTREAM_README.md", fetch(card_url), card_url)]
        # Small deterministic inspection set. It is still evaluation-only and
        # overlaps the full benchmark; it is not a separate held-out split.
        smoke = records[:20] if recipe["id"] == "longmemeval-oracle" else records[:1]
        smoke_path = folder / "smoke-eval.json"
        smoke_path.write_text(json.dumps(smoke, ensure_ascii=False, indent=2), encoding="utf-8")
        entry = {"id": recipe["id"], "license": recipe["license"], "revision": revision,
                 "license_repo_revision": repo_revision, "role": "evaluation-only", "training_allowed_by_project": False,
                 "use": recipe["use"], "record_count": len(records), "smoke_record_count": len(smoke),
                 "files": files, "smoke_sha256": hashlib.sha256(smoke_path.read_bytes()).hexdigest()}
        (folder / "provenance.json").write_text(json.dumps(entry, indent=2), encoding="utf-8")
        entries = [item for item in entries if item["id"] != entry["id"]]
        entries.append(entry)
        print(f"Downloaded {recipe['id']}: {len(records)} top-level records; {len(raw):,} bytes; schema verified.", flush=True)
    manifest = {"createdAt": datetime.now(timezone.utc).isoformat(), "purpose": "Forensic Atlas memory evaluation; no model training or benchmark run performed", "datasets": entries}
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Saved datasets/evaluation/manifest.json", flush=True)


if __name__ == "__main__":
    main()
