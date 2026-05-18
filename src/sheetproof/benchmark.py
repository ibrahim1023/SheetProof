from __future__ import annotations

import json
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sheetproof.assumptions.detector import detect_assumptions
from sheetproof.formulas.extractor import extract_formula_inventory
from sheetproof.graph.builder import build_dependency_graph
from sheetproof.graph.impact import compute_downstream_impact
from sheetproof.risk.lineage import enrich_findings_with_lineage
from sheetproof.risk.rules import (
    dedupe_findings,
    detect_broken_reference_findings,
    detect_formula_inconsistency_findings,
    detect_hardcoded_override_findings,
    detect_hidden_external_dependency_findings,
    detect_volatile_formula_findings,
)
from sheetproof.risk.scorer import score_findings
from sheetproof.workbook.parser import parse_workbook


@dataclass
class BenchmarkSummary:
    workbook: str
    runs: int
    deterministic: bool
    runtime_ms: dict[str, float]
    workbook_stats: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _run_audit_once(workbook: Path) -> tuple[float, dict[str, int]]:
    start = time.perf_counter()
    index = parse_workbook(workbook, deterministic=True)
    formulas = extract_formula_inventory(index)
    graph = build_dependency_graph(formulas)
    impact = compute_downstream_impact(graph)
    _ = detect_assumptions(index, impact, graph)

    findings = []
    findings.extend(detect_formula_inconsistency_findings(formulas))
    findings.extend(detect_hardcoded_override_findings(index))
    findings.extend(detect_hidden_external_dependency_findings(index, formulas))
    findings.extend(detect_volatile_formula_findings(formulas))
    findings.extend(detect_broken_reference_findings(formulas))
    findings = dedupe_findings(findings)
    findings = score_findings(findings, impact)
    _ = enrich_findings_with_lineage(findings, graph, impact)

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    stats = {
        "sheet_count": index.sheet_count,
        "cell_count": sum(s.populated_cells for s in index.sheets),
        "formula_count": len(formulas),
        "finding_count": len(findings),
    }
    return elapsed_ms, stats


def run_audit_benchmark(workbook: Path, runs: int) -> BenchmarkSummary:
    if runs <= 0:
        raise ValueError("runs must be > 0")

    times: list[float] = []
    stats: dict[str, int] | None = None
    for _ in range(runs):
        elapsed_ms, run_stats = _run_audit_once(workbook)
        times.append(elapsed_ms)
        stats = run_stats

    sorted_times = sorted(times)
    p95_idx = max(0, int(round(0.95 * (len(sorted_times) - 1))))
    runtime = {
        "min_ms": round(min(times), 3),
        "avg_ms": round(statistics.fmean(times), 3),
        "p95_ms": round(sorted_times[p95_idx], 3),
        "max_ms": round(max(times), 3),
    }
    return BenchmarkSummary(
        workbook=workbook.name,
        runs=runs,
        deterministic=True,
        runtime_ms=runtime,
        workbook_stats=stats or {},
    )


def write_benchmark_summary(summary: BenchmarkSummary, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out_path


def compare_benchmark_to_baseline(current: BenchmarkSummary, baseline_path: Path, max_regression_pct: float) -> None:
    if not baseline_path.exists():
        raise ValueError(f"Baseline file not found: {baseline_path}")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    base_p95 = float(baseline.get("runtime_ms", {}).get("p95_ms", 0.0))
    cur_p95 = float(current.runtime_ms.get("p95_ms", 0.0))
    if base_p95 <= 0:
        raise ValueError("Baseline p95_ms must be > 0")
    regression = ((cur_p95 - base_p95) / base_p95) * 100.0
    if regression > max_regression_pct:
        raise RuntimeError(
            f"Benchmark regression exceeded threshold: p95_ms baseline={base_p95} current={cur_p95} "
            f"regression={regression:.2f}% threshold={max_regression_pct:.2f}%"
        )
