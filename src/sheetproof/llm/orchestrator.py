from __future__ import annotations

from dataclasses import dataclass
import json
import time
import uuid
from typing import Callable
from typing import TypedDict

from langgraph.graph import END, StateGraph
from sheetproof.llm.schemas import StructuredExplanation
from sheetproof.observability import write_trace


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


class ExplainState(TypedDict):
    prompt: str
    attempt: int
    error: str | None
    parsed: StructuredExplanation | None


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

    start = time.perf_counter()
    state: ExplainState = {
        "prompt": "",
        "attempt": 0,
        "error": None,
        "parsed": None,
    }

    def _build_prompt_node(s: ExplainState) -> ExplainState:
        s["prompt"] = build_prompt()
        return s

    def _provider_call_node(s: ExplainState) -> ExplainState:
        attempt = s["attempt"]
        prompt_text = s["prompt"]
        try:
            _trace(
                {
                    "event": "provider_call",
                    "request_id": request_id,
                    "attempt": attempt,
                    "provider": cfg.provider,
                    "model": cfg.model,
                    "prompt_version": cfg.prompt_version,
                    "prompt_chars": len(prompt_text),
                }
            )
            raw = provider_call(prompt_text)
            normalized = _normalize_provider_json(raw)
            payload = json.loads(normalized)
            parsed = StructuredExplanation.model_validate(_coerce_structured_payload(payload))
            s["parsed"] = parsed
            s["error"] = None
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
            return s
        except Exception as exc:  # noqa: BLE001
            s["error"] = str(exc)
            s["attempt"] = attempt + 1
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
            return s

    def _retry_router(s: ExplainState) -> str:
        if s.get("parsed") is not None:
            return "done"
        if s["attempt"] > cfg.max_retries:
            return "failed"
        return "provider_call"

    def _failed_node(s: ExplainState) -> ExplainState:
        _trace(
            {
                "event": "explain_failed",
                "request_id": request_id,
                "cell": cfg.cell,
                "provider": cfg.provider,
                "model": cfg.model,
                "error": str(s.get("error") or "unknown_error"),
                "latency_ms": int((time.perf_counter() - start) * 1000),
            }
        )
        return s

    graph = StateGraph(ExplainState)
    graph.add_node("build_prompt", _build_prompt_node)  # type: ignore[call-overload]
    graph.add_node("provider_call", _provider_call_node)  # type: ignore[call-overload]
    graph.add_node("failed", _failed_node)  # type: ignore[call-overload]
    graph.set_entry_point("build_prompt")
    graph.add_edge("build_prompt", "provider_call")
    graph.add_conditional_edges(
        "provider_call",
        _retry_router,
        {"provider_call": "provider_call", "failed": "failed", "done": END},
    )
    graph.add_edge("failed", END)

    final_state = graph.compile().invoke(state, {"recursion_limit": cfg.max_steps})
    parsed = final_state.get("parsed")
    if isinstance(parsed, StructuredExplanation):
        return parsed
    err = str(final_state.get("error") or "unknown_error")
    raise RuntimeError(f"Explanation failed after retries: {err}")
