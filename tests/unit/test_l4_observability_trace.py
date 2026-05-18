import json
from pathlib import Path

from sheetproof.observability import write_trace


def test_write_trace_with_phoenix_backend_fallback(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    out = tmp_path / ".sheetproof"
    write_trace(
        {
            "event": "explain_success",
            "request_id": "r1",
            "provider": "ollama",
            "model": "llama3.1:8b",
            "prompt_version": "v1",
            "latency_ms": 10,
            "token_usage": None,
            "error": None,
        },
        out_dir=out,
        backend="phoenix",
    )
    lines = (out / "traces.jsonl").read_text(encoding="utf-8").splitlines()
    assert lines
    payload = json.loads(lines[-1])
    assert payload["event"] == "explain_success"
    assert payload["request_id"] == "r1"
