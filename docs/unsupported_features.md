# Unsupported Feature Attestation

SheetProof uses deterministic warning codes to signal workbook constructs that are currently outside full attestation coverage.

## Warning Taxonomy

- `UNSUPPORTED:VBA_MACROS`
- `UNSUPPORTED:PIVOT_TABLES`
- `UNSUPPORTED:DATA_CONNECTIONS`
- `UNSUPPORTED:SLICERS`
- `UNSUPPORTED:PACKAGE_READ_ERROR`

## Attestation Rules

- `attestation_status = fully_attested` when no unsupported warning codes are detected.
- `attestation_status = cannot_attest` when one or more unsupported warning codes are detected.

## Artifacts

- `.sheetproof/workbook-index.json`: includes `warning_codes` and `attestation_status`.
- `.sheetproof/sheetproof-report.json`: includes workbook attestation fields.
- `.sheetproof/coverage-matrix.json`: parser coverage matrix and warning taxonomy.
- `.sheetproof/gate-result.json`: can include failure `max_unattested_features` when threshold exceeded.
