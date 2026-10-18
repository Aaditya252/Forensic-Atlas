"""Read-only deployment readiness checks. Run with the full stack running."""
import hashlib
import json
import shutil
import sys
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    failures = []

    def check(label, action):
        try:
            if action() is False:
                raise ValueError("check returned false")
            print(f"PASS {label}")
        except Exception as exc:
            failures.append(label)
            print(f"FAIL {label}: {exc}")

    for executable in ("ffmpeg", "ffprobe", "docker"):
        check(executable, lambda name=executable: bool(shutil.which(name)))

    def verify_models():
        for folder in ("phase2", "aasist-l"):
            directory = ROOT / "models" / folder
            manifest = json.loads((directory / "manifest.json").read_text())
            files = manifest.get("files", [{"file": Path(manifest.get("modelPath", "").replace("\\", "/")).name,
                                            "sha256": manifest.get("modelSha256")}])
            for item in files:
                with (directory / item["file"]).open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
                if digest != item["sha256"]:
                    raise ValueError(f"Checksum mismatch: {folder}/{item['file']}")

    check("pinned Qwen and AASIST assets", verify_models)

    def audio_model():
        from backend.audio_screen import load_model
        load_model()

    check("audio dependencies and model load", audio_model)

    def health():
        opener = build_opener(ProxyHandler({}))
        with opener.open("http://127.0.0.1:8100/health", timeout=10) as response:
            result = json.load(response)
        if result.get("service") != "forensic-atlas":
            raise ValueError("Unexpected service")
        if not result.get("graph", {}).get("connected"):
            raise ValueError("FalkorDB disconnected")
        from backend.local_llm import LocalLLM
        if not LocalLLM().status().get("ready"):
            raise ValueError("Qwen unavailable")

    check("live API, FalkorDB and Qwen", health)
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
