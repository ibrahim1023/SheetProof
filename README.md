# SheetProof

SheetProof is a local-first trust layer for business-critical Excel workbooks.

It focuses on deterministic spreadsheet auditing:
- workbook parsing
- formula inventory
- dependency graphing
- formula consistency checks
- hardcoded override detection
- hidden/external dependency detection
- workbook diffing
- assumption extraction
- assumption delta tracking between workbook versions
- risk scoring
- evidence-backed report generation

## Status

Implemented:
- deterministic audit pipeline
- workbook diff pipeline
- local explain (Ollama) with deterministic-artifact guardrails

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
sheetproof --help
pytest
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
```

`explain` requirements:
- run `audit` first for the same workbook (uses `.sheetproof` deterministic artifacts)
- enable local LLM in config (`sheetproof.yml`):

```yaml
llm:
  enabled: true
  provider: "local"
  model: "qwen"
  base_url: "http://localhost:11434"
```

## Output Artifacts (target MVP)

- `.sheetproof/workbook-index.json`
- `sheetproof-report.md`
- `sheetproof-report.json`
- `risk-cells.csv`
- `formula-map.json`
- `dependency-graph.json`
- `assumption-register.csv`
- `workbook-diff.json`
- `assumption-diff.json`
- `reproducibility-manifest.json`

## Policy Packs

Deterministic policy packs are supported:
- `finance`
- `compliance`
- `operations`

Use `--policy-pack` to apply one. Policy packs control deterministic severities, volatile-function handling, and high-risk sheet lists.
