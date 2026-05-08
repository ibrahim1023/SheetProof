# Report Schema

Target report artifacts:

- `sheetproof-report.md`
- `sheetproof-report.json`
- `risk-cells.csv`
- `formula-map.json`
- `dependency-graph.json`
- `assumption-register.csv`
- `workbook-diff.json` (diff mode)
- `assumption-diff.json` (diff mode)
- `gate-result.json` (gate mode)
- `reproducibility-manifest.json`

Each finding must include workbook, sheet, cell, issue type, and deterministic evidence.

## JSON Report Minimum Fields

`sheetproof-report.json` includes:
- `workbook`
- `summary`
- `findings`
- `assumptions`
- `warnings`
- `effective_policy` (when policy packs are applied)

`findings[*]` includes lineage fields:
- `source_cells`
- `dependency_path`
- `impacted_outputs`
- `path_depth`

## Markdown Report Required Sections

`sheetproof-report.md` includes:
- `Executive Summary`
- `Workbook Overview`
- `High-Risk Findings`
- `Assumption Register`
- `Human Review Checklist`
- `Lineage Evidence for High-Risk Findings`
- `Evidence Appendix`
