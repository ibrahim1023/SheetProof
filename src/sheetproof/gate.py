from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from typing import TypedDict

from langgraph.graph import END, StateGraph
from sheetproof.reproducibility import write_stable_json


@dataclass
class GateFailure:
    rule: str
    actual: int
    threshold: int
    reason: str
    evidence: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GateResult:
    mode: str
    passed: bool
    exit_code: int
    failures: list[GateFailure]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "passed": self.passed,
            "exit_code": self.exit_code,
            "failures": [f.to_dict() for f in self.failures],
        }


class GateState(TypedDict):
    result: GateResult | None
    out_path: Path | None


def write_gate_result(result: GateResult, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "gate-result.json"
    write_stable_json(out_file, result.to_dict())
    return out_file


def build_gate_result(mode: str, failures: list[GateFailure]) -> GateResult:
    if not failures:
        return GateResult(mode=mode, passed=True, exit_code=0, failures=[])

    # Deterministic exit-class mapping by dominant failure type.
    code = 10
    rules = {f.rule for f in failures}
    if any("external" in r for r in rules):
        code = 12
    elif any("hidden" in r for r in rules):
        code = 13
    elif any("high_risk" in r for r in rules):
        code = 11

    return GateResult(mode=mode, passed=False, exit_code=code, failures=failures)


def run_gate_flow(mode: str, failures: list[GateFailure], out_dir: Path) -> tuple[GateResult, Path]:
    state: GateState = {"result": None, "out_path": None}

    def _build_result_node(s: GateState) -> GateState:
        s["result"] = build_gate_result(mode=mode, failures=failures)
        return s

    def _write_result_node(s: GateState) -> GateState:
        result = s.get("result")
        if not isinstance(result, GateResult):
            raise RuntimeError("Gate result missing in state")
        s["out_path"] = write_gate_result(result, out_dir)
        return s

    graph = StateGraph(GateState)
    graph.add_node("build_result", _build_result_node)  # type: ignore[call-overload]
    graph.add_node("write_result", _write_result_node)  # type: ignore[call-overload]
    graph.set_entry_point("build_result")
    graph.add_edge("build_result", "write_result")
    graph.add_edge("write_result", END)

    final_state = graph.compile().invoke(state)
    result = final_state.get("result")
    out_path = final_state.get("out_path")
    if not isinstance(result, GateResult) or not isinstance(out_path, Path):
        raise RuntimeError("Gate flow failed to produce result artifact")
    return result, out_path
