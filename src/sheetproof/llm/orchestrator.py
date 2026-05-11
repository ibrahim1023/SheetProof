from __future__ import annotations

from dataclasses import dataclass
import time
import uuid
from typing import Callable

from sheetproof.llm.schemas import StructuredExplanation
from sheetproof.observability import write_trace


@dataclass
class ExplainRunConfig:
    workbook_name: str
    cell: str
    model: str
    max_retries: int = 2


def run_explain_flow(
    cfg: ExplainRunConfig,
    build_prompt: Callable[[], str],
    provider_call: Callable[[str], str],
) -> StructuredExplanation:
    # Explicit state transitions (LangGraph-ready control flow).
    write_trace(
        {
            "event": "explain_start",
            "request_id": str(uuid.uuid4()),
            "workbook": cfg.workbook_name,
            "cell": cfg.cell,
            "model": cfg.model,
        }
    )

    prompt = build_prompt()
    start = time.perf_counter()
    last_err: Exception | None = None
    for attempt in range(cfg.max_retries + 1):
        try:
            write_trace(
                {
                    "event": "provider_call",
                    "attempt": attempt,
                    "provider": "ollama",
                    "model": cfg.model,
                    "prompt_chars": len(prompt),
                }
            )
            raw = provider_call(prompt)
            parsed = StructuredExplanation.model_validate_json(raw)
            write_trace(
                {
                    "event": "explain_success",
                    "attempt": attempt,
                    "cell": cfg.cell,
                    "latency_ms": int((time.perf_counter() - start) * 1000),
                    "output_chars": len(raw),
                }
            )
            return parsed
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            write_trace(
                {
                    "event": "explain_retry",
                    "attempt": attempt,
                    "error": str(exc),
                    "latency_ms": int((time.perf_counter() - start) * 1000),
                }
            )

    assert last_err is not None
    write_trace({"event": "explain_failed", "cell": cfg.cell, "error": str(last_err)})
    raise RuntimeError(f"Explanation failed after retries: {last_err}")
