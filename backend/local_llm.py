"""Small loopback-only llama.cpp adapter with bounded structured responses."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "models" / "phase2" / "manifest.json"


class ModelError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ModelError("LLM_REDIRECT_REJECTED", "The local model endpoint attempted an unexpected redirect.")


class LocalLLM:
    def __init__(self):
        self.config = None
        if MANIFEST.is_file():
            try:
                config = json.loads(MANIFEST.read_text(encoding="utf-8"))
                parsed = urlparse(str(config.get("baseUrl", "")))
                if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "::1", "localhost"} or parsed.username or parsed.password or parsed.query or parsed.fragment:
                    raise ValueError("Only a local model endpoint is allowed.")
                if config.get("enabled") is True and isinstance(config.get("modelId"), str):
                    self.config = config
            except (OSError, ValueError, TypeError):
                self.config = None
        self.opener = build_opener(ProxyHandler({}), _NoRedirect())

    def _request(self, path: str, body=None, timeout=2):
        if not self.config:
            raise ModelError("LLM_NOT_CONFIGURED", "Set up the local Phase 2 model before generating a cited summary.")
        encoded = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(self.config["baseUrl"].rstrip("/") + path, data=encoded,
                          headers={"Content-Type": "application/json", "Accept": "application/json"})
        try:
            with self.opener.open(request, timeout=timeout) as response:
                raw = response.read(128 * 1024 + 1)
            if len(raw) > 128 * 1024:
                raise ModelError("LLM_RESPONSE_TOO_LARGE", "The local model response exceeded its size limit.")
            return json.loads(raw)
        except ModelError:
            raise
        except (HTTPError, URLError, TimeoutError, OSError, ValueError):
            raise ModelError("LOCAL_LLM_UNAVAILABLE", "The local model is not ready or did not return valid JSON. Start the Phase 2 model service and retry.") from None

    def status(self) -> dict:
        if not self.config:
            return {"status": "not-configured", "ready": False}
        result = {"status": "unavailable", "ready": False, **self.model_info()}
        try:
            models = self._request("/models")
            if any(row.get("id") == self.config["modelId"] for row in models.get("data", [])):
                result.update(status="local-ready", ready=True)
        except ModelError:
            pass
        return result

    def model_info(self) -> dict:
        if not self.config:
            return {}
        return {key: self.config.get(key) for key in ("modelId", "upstreamModel", "quantization", "revision", "modelSha256", "runtimeVersion", "trainedByUs")}

    def select_facts(self, messages: list[dict], fact_ids: list[str], required_groups: dict | None = None) -> dict:
        if not self.config:
            raise ModelError("LLM_NOT_CONFIGURED", "The local Phase 2 model is not configured.")
        schema = {"type": "object", "properties": {"selectedFactIds": {"type": "array", "items": {"type": "string", "enum": fact_ids}, "minItems": 1, "maxItems": 6}},
                  "required": ["selectedFactIds"], "additionalProperties": False}
        # Dedicated enum fields enforce coverage without trusting prose instructions.
        groups = required_groups or {}
        if groups:
            schema["properties"]["selectedFactIds"]["maxItems"] = 6 - len(groups)
            for key, ids in groups.items():
                schema["properties"][key] = {"type": "string", "enum": ids}
                schema["required"].append(key)
            messages = [*messages, {"role": "user", "content": "Use the JSON schema: choose one ID for each required category field, then additional IDs in selectedFactIds. Required fields: " + json.dumps(groups)}]
        data = self._request("/chat/completions", {"model": self.config["modelId"], "messages": messages,
                             "temperature": 0, "seed": 42, "max_tokens": 192, "stream": False,
                             "chat_template_kwargs": {"enable_thinking": False}, "reasoning_effort": "none",
                             "response_format": {"type": "json_object", "schema": schema}},
                             timeout=min(max(int(self.config.get("timeoutSeconds", 45)), 5), 45))
        try:
            choice = data["choices"][0]
            if choice.get("finish_reason") != "stop":
                raise ValueError("Incomplete generation")
            output = json.loads(choice["message"]["content"])
            if groups:
                if not isinstance(output, dict) or set(output) != {"selectedFactIds", *groups}:
                    raise ValueError("Missing selection fields")
                if not isinstance(output["selectedFactIds"], list) or any(output[key] not in ids for key, ids in groups.items()):
                    raise ValueError("Invalid required fact")
                output = {"selectedFactIds": list(dict.fromkeys([*(output[key] for key in groups), *output["selectedFactIds"]]))}
            return {"selection": output, "usage": data.get("usage", {})}
        except (KeyError, IndexError, TypeError, ValueError):
            raise ModelError("LLM_INVALID_OUTPUT", "The local model did not finish a valid structured summary selection.") from None
