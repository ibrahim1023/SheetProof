# SheetProof

SheetProof is a local-first spreadsheet trust layer for audit, diff, and gating workflows on `.xlsx` models.  
It is designed so deterministic analysis remains authoritative, while LLM usage is optional and constrained to explanations.

## Core Capabilities

- deterministic workbook audit (parser, formula map, dependency graph, risk detectors, scoring)
- deterministic workbook diff (formula/value/assumption deltas and high-risk changes)
- machine-readable approval gates (`gate-result.json` + deterministic exit codes)
- explain path with strict deterministic-artifact boundary and fail-closed schema validation
- reproducibility artifacts and runtime traces for CI and review workflows

## Technology Stack

### Runtime Libraries

| Library | Purpose |
|---|---|
| `openpyxl` | `.xlsx` parsing, formulas, workbook structure extraction |
| `typer` | CLI application and command surface |
| `rich` | CLI output formatting support |
| `pydantic` | strict explanation schema contracts and validation |
| `langgraph` | workflow orchestration runtime for explain and gate flows |
| `litellm` | unified multi-provider LLM gateway |
| `instructor` | structured-output runtime with schema validation/retries |
| `opentelemetry` SDK/exporters | trace instrumentation and OTLP export |
| `PyYAML` | config and policy-pack loading |

### Dev/Quality Tooling

| Library | Purpose |
|---|---|
| `pytest` | unit/integration test execution |
| `ruff` | linting/static quality checks |
| `mypy` | type checking |
| `promptfoo` (CI via `npx`) | eval regression and policy checks |

## Current Quality Metrics

| Metric | Current Value | Source |
|---|---|---|
| Test suite | `52 passed` | `pytest -q` |
| Lint | Pass | `ruff check src tests` |
| Typecheck | Pass | `mypy src` |
| Explain eval gate pass rate | `66.67%` (`2/3`) | `evals/results/explain_eval_results.json` |
| Benchmark p95 (medium fixture) | `18.213 ms` (3 runs latest) | `evals/results/audit_benchmark_latest.json` |
| Benchmark baselines | small/medium/large class baselines tracked | `evals/results/audit_benchmark_*_baseline.json` |

Note: the explain eval dataset intentionally includes a malformed case that must fail schema validation; this is expected and confirms fail-closed behavior.

## Testing Scope for `.xlsx` Files

Current project testing is strong on deterministic logic and guardrails, but not yet broad enough to claim full real-world workbook coverage.

What is covered now:
- repeated fixture-based unit/integration tests for parser, diff, scoring, gate semantics, firewall behavior, and orchestration
- reproducibility checks across repeated deterministic runs
- benchmark fixture class for performance gating

What still needs expansion:
- wider portfolio of real-world workbook patterns (complex financial models, edge Excel features, large files)
- explicit unsupported-feature matrix and attestation downgrade behavior
- additional parser edge-case fixtures across workbook classes

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
sheetproof --help
pytest -q
```

## Commands

```bash
sheetproof audit workbook.xlsx
sheetproof audit workbook.xlsx --policy-pack finance
sheetproof diff old.xlsx new.xlsx
sheetproof diff old.xlsx new.xlsx --policy-pack compliance
sheetproof gate --workbook workbook.xlsx --max-high-risk-findings 5 --max-external-references 0
sheetproof gate --old-workbook old.xlsx --new-workbook new.xlsx --max-new-hidden-sheets 0
sheetproof explain workbook.xlsx --cell "Summary!F12"
sheetproof eval-explain --dataset evals/datasets/explain_schema_cases.json --output evals/results/explain_eval_results.json
sheetproof benchmark-audit --workbook examples/benchmark_medium.xlsx --runs 5 --output evals/results/audit_benchmark_latest.json
sheetproof benchmark-audit --workbook examples/benchmark_small.xlsx --runs 3 --baseline evals/results/audit_benchmark_small_baseline.json --max-regression-pct 100
sheetproof benchmark-audit --workbook examples/benchmark_medium.xlsx --runs 3 --baseline evals/results/audit_benchmark_medium_baseline.json --max-regression-pct 120
sheetproof benchmark-audit --workbook examples/benchmark_large.xlsx --runs 2 --baseline evals/results/audit_benchmark_large_baseline.json --max-regression-pct 150
```

## Explain Configuration

`explain` requires deterministic artifacts from a prior `audit` run for the same workbook.

```yaml
schema_version: 1
local_only: false
observability:
  trace_backend: "local"   # local | otel | langfuse | phoenix
  primary_backend: "phoenix" # phoenix | langfuse
llm:
  enabled: true
  provider: "local"        # local | ollama | openai | anthropic | gemini
  model: "qwen"
  base_url: "http://localhost:11434"
  prompt_version: "v1"
  timeout_seconds: 40
  max_retries: 2
  max_steps: 20
  constrained_output_engine: "instructor"  # instructor | pydantic | outlines | pydanticai
```

If `local_only: true`, hosted providers are blocked.

Optional tracing backends:
- `langfuse`: `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`
- `phoenix`: `PHOENIX_COLLECTOR_ENDPOINT`
- `otel`: `OTEL_EXPORTER_OTLP_ENDPOINT`

Promptfoo evals (CI-compatible):

```bash
npx promptfoo@latest eval -c evals/promptfooconfig.yaml
```

## Output Artifacts

- `.sheetproof/workbook-index.json`
- `.sheetproof/formula-map.json`
- `.sheetproof/dependency-graph.json`
- `.sheetproof/sheetproof-report.md`
- `.sheetproof/sheetproof-report.json`
- `.sheetproof/risk-cells.csv`
- `.sheetproof/assumption-register.csv`
- `.sheetproof/workbook-diff.json`
- `.sheetproof/assumption-diff.json`
- `.sheetproof/reproducibility-manifest.json`
- `.sheetproof/traces.jsonl`
- `.sheetproof/explanations.json`
- `.sheetproof/gate-result.json`
- `.sheetproof/coverage-matrix.json`
- `.sheetproof/approval-trail.json` (when gate approval inputs are provided)
- `evals/results/audit_benchmark_small_baseline.json`
- `evals/results/audit_benchmark_medium_baseline.json`
- `evals/results/audit_benchmark_large_baseline.json`
- `evals/results/audit_benchmark_latest.json` (local/runtime; gitignored)

## Policy Packs

Deterministic policy packs:
- `finance`
- `compliance`
- `operations`

Use `--policy-pack` to apply one. Packs control severity overrides, volatile-function handling, and high-risk sheet lists.
