# ADR: Constrained Explanation Output Engine

Date: 2026-05-18

## Context

SheetProof explanation outputs must remain schema-valid and fail closed without affecting deterministic findings.
We evaluated options for constrained generation:

- Pydantic validation (current)
- Outlines
- PydanticAI

## Decision

Use `pydantic` as the default constrained output engine for MVP and keep `outlines` / `pydanticai` as configuration options for future adoption.

## Rationale

- Pydantic is already integrated and proven in tests.
- No additional runtime dependency is required for MVP stability.
- The configuration flag allows future provider-side constrained decoding experiments without changing the deterministic core boundary.

## Consequences

- Schema validation remains fail-closed and mandatory.
- Outlines/PydanticAI are evaluated as future extensions, not required for current completion.
