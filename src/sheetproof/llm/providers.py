from __future__ import annotations

import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ProviderCallError(RuntimeError):
    pass


def _post_json(
    url: str,
    payload: dict,
    headers: dict[str, str],
    timeout: int = 40,
    max_retries: int = 2,
) -> dict:
    req = Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )

    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            with urlopen(req, timeout=timeout) as resp:  # noqa: S310
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            last_exc = exc
            status = getattr(exc, "code", 0)
            # Retry rate-limit and transient server errors.
            if status in {429, 500, 502, 503, 504} and attempt < max_retries:
                time.sleep(min(0.5 * (2**attempt), 2.0))
                continue
            raise ProviderCallError(f"HTTP error from provider: status={status}") from exc
        except URLError as exc:
            last_exc = exc
            if attempt < max_retries:
                time.sleep(min(0.5 * (2**attempt), 2.0))
                continue
            raise ProviderCallError("Network error calling provider") from exc

    assert last_exc is not None
    raise ProviderCallError(f"Provider call failed after retries: {last_exc}")


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
    root = (base_url or "https://api.openai.com/v1").rstrip("/")
    payload = {
        "model": model,
        "input": prompt,
    }
    body = _post_json(
        f"{root}/responses",
        payload,
        {"Authorization": f"Bearer {key}"},
        timeout=timeout,
        max_retries=max_retries,
    )

    out = body.get("output", [])
    for item in out:
        for part in item.get("content", []):
            text = part.get("text")
            if text:
                return str(text)
    text = body.get("output_text")
    if text:
        return str(text)
    raise ProviderCallError("OpenAI response did not include text output")


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

    payload = {
        "model": model,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }
    body = _post_json(
        "https://api.anthropic.com/v1/messages",
        payload,
        {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
        timeout=timeout,
        max_retries=max_retries,
    )
    content = body.get("content", [])
    for part in content:
        text = part.get("text")
        if text:
            return str(text)
    raise ProviderCallError("Anthropic response did not include text output")


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

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    body = _post_json(url, payload, headers={}, timeout=timeout, max_retries=max_retries)

    candidates = body.get("candidates", [])
    for cand in candidates:
        parts = cand.get("content", {}).get("parts", [])
        for p in parts:
            text = p.get("text")
            if text:
                return str(text)
    raise ProviderCallError("Gemini response did not include text output")
