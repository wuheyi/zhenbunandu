from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


DEFAULT_LLM_BASE_URL = "https://api.deepseek.com"
DEFAULT_LLM_MODEL = "deepseek-v4-flash"


def normalize_llm_settings(payload: dict[str, Any] | None) -> dict[str, str]:
    payload = payload or {}
    return {
        "base_url": str(payload.get("base_url") or DEFAULT_LLM_BASE_URL).strip().rstrip("/"),
        "model": str(payload.get("model") or DEFAULT_LLM_MODEL).strip(),
        "api_key": str(payload.get("api_key") or "").strip(),
    }


@dataclass(frozen=True)
class LLMResult:
    text: str
    used_llm: bool
    error: str = ""


class LLMClient:
    def __init__(self, settings: dict[str, Any] | None, transport: httpx.BaseTransport | None = None):
        self.settings = normalize_llm_settings(settings)
        self._transport = transport

    @property
    def configured(self) -> bool:
        return bool(self.settings["api_key"])

    @property
    def model(self) -> str:
        return self.settings["model"]

    @property
    def base_url(self) -> str:
        return self.settings["base_url"]

    def public_config(self) -> dict[str, str]:
        return {"base_url": self.base_url, "model": self.model}

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        fallback: str,
        temperature: float = 0.4,
        max_tokens: int = 700,
    ) -> LLMResult:
        if not self.configured:
            return LLMResult(fallback, used_llm=False, error="LLM 未配置")

        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": False,
            }
            headers = {
                "Authorization": f"Bearer {self.settings['api_key']}",
                "Content-Type": "application/json",
            }
            with httpx.Client(timeout=25, transport=self._transport) as client:
                response = client.post(self._chat_url(), json=payload, headers=headers)
                response.raise_for_status()
            data = response.json()
            text = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            if not text:
                return LLMResult(fallback, used_llm=False, error="LLM 返回为空")
            return LLMResult(text, used_llm=True)
        except Exception as exc:  # pragma: no cover - exact provider errors vary
            return LLMResult(fallback, used_llm=False, error=self._safe_error(exc))

    def _chat_url(self) -> str:
        return f"{self.base_url}/chat/completions"

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        if isinstance(exc, httpx.HTTPStatusError):
            message = f"HTTP {exc.response.status_code}"
            try:
                body = exc.response.json()
                provider_message = body.get("error", {}).get("message") or body.get("message")
                if provider_message:
                    message = f"{message}: {provider_message}"
            except Exception:
                pass
            return message[:240]
        return str(exc)[:240]
