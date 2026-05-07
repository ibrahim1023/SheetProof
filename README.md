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
sheetproof diff old.xlsx new.xlsx
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
