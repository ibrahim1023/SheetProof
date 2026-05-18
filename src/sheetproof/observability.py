from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_TRACER_READY = False


def _ensure_tracer() -> None:
    global _TRACER_READY
    if _TRACER_READY:
        return
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    provider = TracerProvider(resource=Resource.create({"service.name": "sheetproof"}))
    if endpoint:
        exporter = OTLPSpanExporter(endpoint=endpoint.rstrip("/") + "/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _TRACER_READY = True


def write_trace(
    event: dict[str, Any],
    out_dir: Path = Path(".sheetproof"),
    backend: str | None = None,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "traces.jsonl"
    payload = dict(event)
    payload.setdefault("ts_unix", time.time())
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    _emit_otel(payload, backend=backend)
    return path


def _emit_otel(event: dict[str, Any], backend: str | None = None) -> None:
    backend_value = backend if backend is not None else os.getenv("SHEETPROOF_TRACE_BACKEND", "local")
    mode = str(backend_value).strip().lower()
    # Always allow local mode; OTel export becomes active when endpoint is configured.
    if mode not in {"local", "langfuse", "phoenix", "otel"}:
        return
    try:
        _ensure_tracer()
        tracer = trace.get_tracer("sheetproof.observability")
        name = str(event.get("event", "sheetproof_event"))
        with tracer.start_as_current_span(name) as span:
            span.set_attribute("sheetproof.event", name)
            for k, v in event.items():
                if v is None:
                    continue
                key = f"sheetproof.{k}"
                if isinstance(v, (bool, int, float, str)):
                    span.set_attribute(key, v)
                else:
                    span.set_attribute(key, json.dumps(v, sort_keys=True))
    except Exception:  # noqa: BLE001
        return
