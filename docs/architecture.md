# Architecture

SheetProof follows a deterministic-first pipeline:

1. Parse workbook structure and cells
2. Extract formulas and references
3. Build dependency graph
4. Run deterministic detectors
5. Compute deterministic risk scores
6. Generate evidence-backed artifacts
7. Optionally produce local LLM explanations from deterministic outputs

No LLM output is allowed to alter risk scoring or factual findings.

## Explain Path

- Provider: local Ollama (`/api/chat`)
- Explain command is read-only and consumes existing deterministic artifacts:
  - `.sheetproof/sheetproof-report.json`
  - `.sheetproof/formula-map.json`
  - `.sheetproof/dependency-graph.json`
- Guardrails:
  - explain fails closed if required deterministic artifacts are missing
  - explain fails if artifact workbook does not match requested workbook
  - explain cannot write/modify findings, severities, or risk scores
