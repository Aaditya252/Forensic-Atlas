"""Fetch pinned Qwen weights and official llama.cpp CPU binaries; no training."""
from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models" / "phase2"
RUNTIME_DIR = ROOT / "local-runtime" / "llama-b11718"
REVISION = "f6d5376be1edb4d416d56da11e5397a961aca8ae"
MODEL_FILE = "Qwen3.5-2B-Q4_K_M.gguf"
MODEL_SHA = "aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223"
RUNTIME_SHA = "92cc529b29a43f9a30e21d490cb2e95062acd0b59af6fee8b3b52b28074f838c"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, destination: Path, expected_size: int, expected_sha: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size == expected_size and sha(destination) == expected_sha:
        print(f"Verified cached {destination.name}", flush=True)
        return
    partial = destination.with_suffix(destination.suffix + ".part")
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "ForensicAtlas-Phase2/1.0"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    with urlopen(Request(url, headers=headers), timeout=90) as response:
        resume = offset > 0 and response.status == 206
        written = offset if resume else 0
        milestone = written // (128 * 1024 * 1024)
        with partial.open("ab" if resume else "wb") as stream:
            while block := response.read(1024 * 1024):
                written += len(block)
                if written > expected_size:
                    raise ValueError("Download exceeded the pinned source size.")
                stream.write(block)
                if written // (128 * 1024 * 1024) > milestone:
                    milestone = written // (128 * 1024 * 1024)
                    print(f"{destination.name}: {written / expected_size:.0%}", flush=True)
    if partial.stat().st_size != expected_size or sha(partial) != expected_sha:
        raise ValueError(f"Source size/checksum mismatch: {destination.name}; file was not activated.")
    partial.replace(destination)
    print(f"Verified {destination.name}: {expected_size:,} bytes", flush=True)


def small_file(url: str, target: Path) -> None:
    with urlopen(Request(url, headers={"User-Agent": "ForensicAtlas-Phase2/1.0"}), timeout=30) as response:
        data = response.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError("Unexpected metadata size.")
    target.write_bytes(data)


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    archive = RUNTIME_DIR.parent / "llama-b11718-bin-win-cpu-x64.zip"
    runtime_url = "https://github.com/ggml-org/llama.cpp/releases/download/b11718/llama-b11718-bin-win-cpu-x64.zip"
    model_url = f"https://huggingface.co/unsloth/Qwen3.5-2B-GGUF/resolve/{REVISION}/{MODEL_FILE}"
    download(runtime_url, archive, 19662572, RUNTIME_SHA)
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            candidate = (RUNTIME_DIR / member.filename).resolve()
            if not candidate.is_relative_to(RUNTIME_DIR.resolve()):
                raise ValueError("Unsafe runtime archive path.")
        bundle.extractall(RUNTIME_DIR)
    small_file("https://raw.githubusercontent.com/ggml-org/llama.cpp/b11718/LICENSE", RUNTIME_DIR / "LICENSE")
    small_file(f"https://huggingface.co/unsloth/Qwen3.5-2B-GGUF/resolve/{REVISION}/README.md", MODEL_DIR / "UPSTREAM_README.md")
    small_file("https://huggingface.co/Qwen/Qwen3.5-2B/raw/main/LICENSE", MODEL_DIR / "LICENSE")
    download(model_url, MODEL_DIR / MODEL_FILE, 1280835840, MODEL_SHA)
    executable = next(RUNTIME_DIR.rglob("llama-server.exe"), None)
    if executable is None:
        raise ValueError("The verified runtime archive has no llama-server.exe.")
    manifest = {"configuredAt": datetime.now(timezone.utc).isoformat(), "enabled": True,
                "modelId": "forensic-atlas-qwen35-2b", "upstreamModel": "Qwen/Qwen3.5-2B",
                "quantizationRepo": "unsloth/Qwen3.5-2B-GGUF", "revision": REVISION,
                "quantization": "Q4_K_M", "license": "Apache-2.0", "modelSha256": MODEL_SHA,
                "modelPath": str((MODEL_DIR / MODEL_FILE).relative_to(ROOT)),
                "runtimePath": str(executable.relative_to(ROOT)), "runtimeVersion": "b11718",
                "runtimeSha256": RUNTIME_SHA, "baseUrl": "http://127.0.0.1:8111/v1",
                "contextTokens": 4096, "timeoutSeconds": 90, "trainedByUs": False,
                "sources": {"model": model_url, "runtime": runtime_url}}
    (MODEL_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Phase 2 model and runtime ready. No training performed.", flush=True)


if __name__ == "__main__":
    main()
