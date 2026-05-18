from __future__ import annotations

import argparse
from pathlib import Path

from sheetproof.benchmark import (
    compare_benchmark_to_baseline,
    run_audit_benchmark,
    write_benchmark_summary,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic audit benchmark.")
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evals/results/audit_benchmark_latest.json"),
    )
    parser.add_argument("--baseline", type=Path, default=None)
    parser.add_argument("--max-regression-pct", type=float, default=25.0)
    args = parser.parse_args()

    summary = run_audit_benchmark(args.workbook, runs=args.runs)
    write_benchmark_summary(summary, args.output)
    print(
        "runtime_ms:",
        f"min={summary.runtime_ms['min_ms']}",
        f"avg={summary.runtime_ms['avg_ms']}",
        f"p95={summary.runtime_ms['p95_ms']}",
        f"max={summary.runtime_ms['max_ms']}",
    )

    if args.baseline is not None:
        compare_benchmark_to_baseline(summary, args.baseline, args.max_regression_pct)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
