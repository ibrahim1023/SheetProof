# Harness Compliance Map

This file maps repository artifacts to `agent_context.md` requirements.

## Required Repository Context

- `docs/decisions/`: present with ADR and process README
- `agents/generated/`: present for generated orientation artifacts

## Session and State

- durable local state tracking is used for execution continuity

## Validation Layer

- project validation commands: `pytest`, `ruff check .`, `mypy src`
- Baseline tests present in `tests/`

## Evaluation Layer

- `evals/` scaffold present:
  - `evals/datasets/`
  - `evals/rubrics/`
  - `evals/results/`
- Process constraints documented in `evals/README.md`

## Deterministic vs LLM Boundary

- Boundary documented in:
  - `docs/architecture.md`
  - `docs/decisions/0001-deterministic-first.md`

## Open Gaps (Implementation, not policy)

- Eval runner scripts not yet implemented
- No observability/tracing implementation yet (planned for later runtime milestones)
- Hosted provider integrations (OpenAI/Anthropic/Gemini) intentionally deferred; Ollama local explain is implemented first
