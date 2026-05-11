from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen


def _post_json(url: str, payload: dict, headers: dict[str, str], timeout: int = 40) -> dict:
    req = Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def call_openai(prompt: str, model: str, base_url: str | None = None, api_key: str | None = None) -> str:
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
    )

    # Best-effort extraction from Responses API shape.
    out = body.get("output", [])
    for item in out:
        for part in item.get("content", []):
            text = part.get("text")
            if text:
                return str(text)
    text = body.get("output_text")
    if text:
        return str(text)
    raise RuntimeError("OpenAI response did not include text output")


def call_anthropic(prompt: str, model: str, api_key: str | None = None) -> str:
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
    )
    content = body.get("content", [])
    for part in content:
        text = part.get("text")
        if text:
            return str(text)
    raise RuntimeError("Anthropic response did not include text output")


def call_gemini(prompt: str, model: str, api_key: str | None = None) -> str:
    key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required for provider=gemini")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    )
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}],
            }
        ]
    }
    body = _post_json(url, payload, headers={})

    candidates = body.get("candidates", [])
    for cand in candidates:
        parts = cand.get("content", {}).get("parts", [])
        for p in parts:
            text = p.get("text")
            if text:
                return str(text)
    raise RuntimeError("Gemini response did not include text output")
