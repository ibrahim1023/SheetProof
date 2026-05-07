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
