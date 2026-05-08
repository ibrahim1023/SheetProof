from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

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
