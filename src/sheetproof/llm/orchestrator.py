from __future__ import annotations

from dataclasses import dataclass
import json
import time
import uuid
from typing import Callable

from sheetproof.llm.schemas import StructuredExplanation
from sheetproof.observability import write_trace
from sheetproof.orchestration.graph import GraphState, run_state_graph


@dataclass
class ExplainRunConfig:
    workbook_name: str
    cell: str
    model: str
    provider: str = "unknown"
    prompt_version: str = "v1"
    trace_backend: str = "local"
    max_retries: int = 2
    max_steps: int = 20


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
    def _trace(event: dict) -> None:
        write_trace(event, backend=cfg.trace_backend)

    request_id = str(uuid.uuid4())
    _trace(
        {
            "event": "explain_start",
            "request_id": request_id,
            "workbook": cfg.workbook_name,
            "cell": cfg.cell,
            "provider": cfg.provider,
            "model": cfg.model,
            "prompt_version": cfg.prompt_version,
        }
    )

    prompt = ""
    start = time.perf_counter()
    attempt = 0
    last_err: Exception | None = None
    parsed: StructuredExplanation | None = None

    def _node_runner(state: GraphState) -> str | None:
        nonlocal prompt, attempt, last_err, parsed
        if state.node == "build_prompt":
            prompt = build_prompt()
            return "provider_call"
        if state.node == "provider_call":
            try:
                _trace(
                    {
                        "event": "provider_call",
                        "request_id": request_id,
                        "attempt": attempt,
                        "provider": cfg.provider,
                        "model": cfg.model,
                        "prompt_version": cfg.prompt_version,
                        "prompt_chars": len(prompt),
                    }
                )
                raw = provider_call(prompt)
                normalized = _normalize_provider_json(raw)
                payload = json.loads(normalized)
                parsed = StructuredExplanation.model_validate(_coerce_structured_payload(payload))
                _trace(
                    {
                        "event": "explain_success",
                        "request_id": request_id,
                        "attempt": attempt,
                        "provider": cfg.provider,
                        "model": cfg.model,
                        "cell": cfg.cell,
                        "latency_ms": int((time.perf_counter() - start) * 1000),
                        "output_chars": len(raw),
                        "token_usage": None,
                    }
                )
                return None
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                _trace(
                    {
                        "event": "explain_retry",
                        "request_id": request_id,
                        "attempt": attempt,
                        "provider": cfg.provider,
                        "model": cfg.model,
                        "error": str(exc),
                        "latency_ms": int((time.perf_counter() - start) * 1000),
                    }
                )
                attempt += 1
                if attempt > cfg.max_retries:
                    return "failed"
                return "provider_call"
        if state.node == "failed":
            assert last_err is not None
            _trace(
                {
                    "event": "explain_failed",
                    "request_id": request_id,
                    "cell": cfg.cell,
                    "provider": cfg.provider,
                    "model": cfg.model,
                    "error": str(last_err),
                    "latency_ms": int((time.perf_counter() - start) * 1000),
                }
            )
            return None
        raise RuntimeError(f"Unknown explain node `{state.node}`")

    run_state_graph(start_node="build_prompt", max_steps=cfg.max_steps, run_node=_node_runner)
    if parsed is not None:
        return parsed
    assert last_err is not None
    raise RuntimeError(f"Explanation failed after retries: {last_err}")
