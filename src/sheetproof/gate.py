from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sheetproof.orchestration.graph import GraphState, run_state_graph
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
    result: GateResult | None = None
    out_path: Path | None = None

    def _node_runner(state: GraphState) -> str | None:
        nonlocal result, out_path
        if state.node == "build_result":
            result = build_gate_result(mode=mode, failures=failures)
            return "write_result"
        if state.node == "write_result":
            assert result is not None
            out_path = write_gate_result(result, out_dir)
            return None
        raise RuntimeError(f"Unknown gate node `{state.node}`")

    run_state_graph(start_node="build_result", max_steps=4, run_node=_node_runner)
    assert result is not None
    assert out_path is not None
    return result, out_path
