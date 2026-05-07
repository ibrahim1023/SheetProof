# Harness Compliance Map

This file maps repository artifacts to `agent_context.md` requirements.

## Required Repository Context

- `AGENTS.md`: present, includes commands, gates, guardrails, loop controls
- `scope.md`: present, source design intent
- `task.md`: present, structured tasks with acceptance + validation gates
- `docs/decisions/`: present with ADR and process README
- `agents/generated/`: present for generated orientation artifacts

## Session and State

- `progress.md`: present for durable state and next-step continuity

## Validation Layer

- Commands declared in `AGENTS.md`: `pytest`, `ruff check .`, `mypy src`
- Baseline tests present in `tests/`

## Evaluation Layer

- `evals/` scaffold present:
  - `evals/datasets/`
  - `evals/rubrics/`
  - `evals/results/`
- Process constraints documented in `evals/README.md`

## Deterministic vs LLM Boundary

- Boundary documented in:
  - `AGENTS.md`
  - `docs/architecture.md`
  - `docs/decisions/0001-deterministic-first.md`

## Open Gaps (Implementation, not policy)

- Eval runner scripts not yet implemented
- No observability/tracing implementation yet (planned for later runtime milestones)
- Hosted provider integrations (OpenAI/Anthropic/Gemini) intentionally deferred; Ollama local explain is implemented first
