# Performance SLO (Initial Baseline)

Benchmarks are enforced per workbook class using deterministic audit runs.

## Baselines

- Small class baseline: `evals/results/audit_benchmark_small_baseline.json`
- Medium class baseline: `evals/results/audit_benchmark_medium_baseline.json`
- Large class baseline: `evals/results/audit_benchmark_large_baseline.json`

## CI Regression Thresholds

- Small: max p95 regression `100%`
- Medium: max p95 regression `120%`
- Large: max p95 regression `150%`

These thresholds are intentionally generous for early-stage stability and should be tightened as workloads and infrastructure stabilize.
