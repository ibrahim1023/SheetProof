from __future__ import annotations

import os
from typing import Any

from litellm import completion


class ProviderCallError(RuntimeError):
    pass


def _as_text(resp: Any) -> str:
    try:
        choices = getattr(resp, "choices", None) or []
        if choices:
            msg = getattr(choices[0], "message", None) or {}
            content = getattr(msg, "content", None) if not isinstance(msg, dict) else msg.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
    except Exception:  # noqa: BLE001
        pass
    raise ProviderCallError("LiteLLM response did not include text output")


def _call_litellm(
    provider_model: str,
    prompt: str,
    timeout: int = 40,
    max_retries: int = 2,
    api_base: str | None = None,
    api_key: str | None = None,
) -> str:
    kwargs: dict[str, Any] = {
        "model": provider_model,
        "messages": [{"role": "user", "content": prompt}],
        "timeout": timeout,
        "num_retries": max_retries,
    }
    if api_base:
        kwargs["api_base"] = api_base
    if api_key:
        kwargs["api_key"] = api_key
    try:
        resp = completion(**kwargs)
        return _as_text(resp)
    except Exception as exc:  # noqa: BLE001
        raise ProviderCallError(f"LiteLLM provider call failed: {exc}") from exc


def call_openai(
    prompt: str,
    model: str,
    base_url: str | None = None,
    api_key: str | None = None,
    timeout: int = 40,
    max_retries: int = 2,
) -> str:
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is required for provider=openai")
    return _call_litellm(
        provider_model=f"openai/{model}",
        prompt=prompt,
        timeout=timeout,
        max_retries=max_retries,
        api_base=base_url,
        api_key=key,
    )


def call_anthropic(
    prompt: str,
    model: str,
    api_key: str | None = None,
    timeout: int = 40,
    max_retries: int = 2,
) -> str:
    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is required for provider=anthropic")
    return _call_litellm(
        provider_model=f"anthropic/{model}",
        prompt=prompt,
        timeout=timeout,
        max_retries=max_retries,
        api_key=key,
    )


def call_gemini(
    prompt: str,
    model: str,
    api_key: str | None = None,
    timeout: int = 40,
    max_retries: int = 2,
) -> str:
    key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required for provider=gemini")
    return _call_litellm(
        provider_model=f"gemini/{model}",
        prompt=prompt,
        timeout=timeout,
        max_retries=max_retries,
        api_key=key,
    )
