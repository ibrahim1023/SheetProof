# ADR 0001: Deterministic-First Analysis

## Status
Accepted

## Context
Workbook trust decisions require reproducible evidence and cannot depend on non-deterministic model output.

## Decision
Risk scoring, formula consistency checks, override detection, dependency mapping, and diffing remain deterministic.
LLM behavior is optional and restricted to explanation/summarization.

## Consequences
- Better reproducibility and auditability
- Slower feature velocity for fuzzy semantic tasks
- Clear boundary between validation and narrative output
