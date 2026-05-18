from __future__ import annotations

from dataclasses import dataclass
import json
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


def _normalize_provider_json(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            return "\n".join(lines).strip()
    return text


def _coerce_structured_payload(payload: dict) -> dict:
    summary = payload.get("summary")
    if isinstance(summary, dict):
        summary = summary.get("text") or summary.get("summary") or json.dumps(summary, sort_keys=True)
    elif summary is None:
        summary = ""

    def _normalize_list(items: object, preferred_keys: tuple[str, ...]) -> list[str]:
        if not isinstance(items, list):
            return []
        out: list[str] = []
        for item in items:
            if isinstance(item, str):
                out.append(item)
                continue
            if isinstance(item, dict):
                for key in preferred_keys:
                    value = item.get(key)
                    if isinstance(value, str):
                        out.append(value)
                        break
        return out

    risks = _normalize_list(payload.get("risks"), ("risk", "text", "reason"))
    reviewer_actions = _normalize_list(payload.get("reviewer_actions"), ("action", "text", "reason"))

    citations = payload.get("citations")
    normalized_citations = []
    if isinstance(citations, list):
        for citation in citations:
            if not isinstance(citation, dict):
                continue
            cell = citation.get("cell")
            reason = citation.get("reason")
            if isinstance(cell, str) and isinstance(reason, str):
                normalized_citations.append({"cell": cell, "reason": reason})

    return {
        "summary": summary,
        "risks": risks,
        "reviewer_actions": reviewer_actions,
        "citations": normalized_citations,
    }


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
            normalized = _normalize_provider_json(raw)
            payload = json.loads(normalized)
            parsed = StructuredExplanation.model_validate(_coerce_structured_payload(payload))
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
