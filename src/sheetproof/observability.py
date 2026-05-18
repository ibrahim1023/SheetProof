from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


def write_trace(
    event: dict[str, Any],
    out_dir: Path = Path(".sheetproof"),
    backend: str | None = None,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / 'traces.jsonl'
    event = dict(event)
    event.setdefault('ts_unix', time.time())
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')
    _emit_external_trace(event, backend=backend)
    return path


def _emit_external_trace(event: dict[str, Any], backend: str | None = None) -> None:
    backend_value = backend if backend is not None else os.getenv("SHEETPROOF_TRACE_BACKEND", "")
    backend = str(backend_value).strip().lower()
    if backend == "langfuse":
        _emit_langfuse(event)
    elif backend == "phoenix":
        _emit_phoenix(event)


def _emit_langfuse(event: dict[str, Any]) -> None:
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com").rstrip("/")
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
    if not public_key or not secret_key:
        return
    # Best-effort legacy ingestion event (fail-open for observability export).
    payload = {
        "batch": [
            {
                "id": str(event.get("request_id", f"evt-{int(time.time() * 1000)}")),
                "type": "event-create",
                "timestamp": event.get("ts_unix", time.time()),
                "body": {
                    "name": str(event.get("event", "sheetproof_event")),
                    "metadata": event,
                },
            }
        ]
    }
    auth = f"{public_key}:{secret_key}".encode("utf-8")
    import base64

    req = Request(
        url=f"{host}/api/public/ingestion",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {base64.b64encode(auth).decode('utf-8')}",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=3):  # noqa: S310
            pass
    except Exception:  # noqa: BLE001
        return


def _emit_phoenix(event: dict[str, Any]) -> None:
    endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "").rstrip("/")
    if not endpoint:
        return
    # Minimal JSON payload; endpoint is expected to accept HTTP traces-style payloads.
    payload = {"resourceSpans": [{"scopeSpans": [{"spans": [{"name": str(event.get("event", "sheetproof_event")), "attributes": [{"key": k, "value": {"stringValue": str(v)}} for k, v in event.items() if k != "event"]}]}]}]}
    url = endpoint if endpoint.endswith("/v1/traces") else f"{endpoint}/v1/traces"
    req = Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=3):  # noqa: S310
            pass
    except Exception:  # noqa: BLE001
        return
