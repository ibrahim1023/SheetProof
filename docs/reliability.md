# Reliability Reporting

SheetProof reliability is measured using deterministic eval result artifacts and threshold gating.

## Generated Artifact

- `evals/results/reliability_metrics.json`

Fields include:

- `total_cases`
- `passed_cases`
- `failed_cases`
- `pass_rate`
- `refusal_total`
- `refusal_passed`
- `refusal_correctness_rate`
- `failure_taxonomy`

## CI Gate

The `reliability-report` command enforces thresholds:

- minimum overall pass rate
- minimum refusal correctness rate

Non-compliance exits non-zero and blocks the workflow.

## Longitudinal Tracking

Store each release’s `reliability_metrics.json` in CI artifacts or release notes to track drift in:

- schema stability failures
- faithfulness failure counts
- refusal correctness trend
