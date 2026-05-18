from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sheetproof.config.defaults import DEFAULT_CONFIG

ALLOWED_SEVERITIES = {"low", "medium", "high"}
ALLOWED_VOLATILE_MODES = {"allow", "warn", "deny"}
ALLOWED_TRACE_BACKENDS = {"local", "langfuse", "phoenix", "otel"}
ALLOWED_PRIMARY_BACKENDS = {"phoenix", "langfuse"}
ALLOWED_CONSTRAINED_ENGINES = {"pydantic", "outlines", "pydanticai", "instructor"}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _validate_config(config: dict[str, Any]) -> None:
    schema_version = config.get("schema_version")
    if schema_version != 1:
        raise ValueError(f"Invalid config schema_version: {schema_version}. Expected 1.")

    if not isinstance(config.get("local_only", False), bool):
        raise ValueError("local_only must be a boolean")

    observability = config.get("observability", {})
    if observability and not isinstance(observability, dict):
        raise ValueError("observability must be a mapping when provided")
    trace_backend = (observability or {}).get("trace_backend", "local")
    if trace_backend not in ALLOWED_TRACE_BACKENDS:
        raise ValueError(
            f"observability.trace_backend must be one of {sorted(ALLOWED_TRACE_BACKENDS)}"
        )
    primary_backend = (observability or {}).get("primary_backend", "phoenix")
    if primary_backend not in ALLOWED_PRIMARY_BACKENDS:
        raise ValueError(
            f"observability.primary_backend must be one of {sorted(ALLOWED_PRIMARY_BACKENDS)}"
        )

    risk = config.get("risk", {})
    if not isinstance(risk.get("high_risk_sheets", []), list):
        raise ValueError("risk.high_risk_sheets must be a list")

    volatile_mode = risk.get("volatile_mode", "warn")
    if volatile_mode not in ALLOWED_VOLATILE_MODES:
        raise ValueError(
            f"risk.volatile_mode must be one of {sorted(ALLOWED_VOLATILE_MODES)}"
        )

    sev = risk.get("severity_overrides", {})
    if not isinstance(sev, dict):
        raise ValueError("risk.severity_overrides must be a mapping")
    for k, v in sev.items():
        if v not in ALLOWED_SEVERITIES:
            raise ValueError(f"Invalid severity `{v}` for `{k}`")

    packs = config.get("policy_packs", {})
    if not isinstance(packs, dict):
        raise ValueError("policy_packs must be a mapping")
    for pack_name, pack_cfg in packs.items():
        if not isinstance(pack_cfg, dict):
            raise ValueError(f"policy_packs.{pack_name} must be a mapping")
        metadata = pack_cfg.get("metadata")
        if not isinstance(metadata, dict):
            raise ValueError(f"policy_packs.{pack_name}.metadata must be a mapping")
        for field in ("version", "owner", "rationale", "updated_at"):
            if not isinstance(metadata.get(field), str) or not metadata.get(field):
                raise ValueError(f"policy_packs.{pack_name}.metadata.{field} must be a non-empty string")

    llm = config.get("llm", {})
    if llm and not isinstance(llm, dict):
        raise ValueError("llm must be a mapping when provided")
    if isinstance(llm, dict):
        timeout_s = llm.get("timeout_seconds", 40)
        retries = llm.get("max_retries", 2)
        max_steps = llm.get("max_steps", 20)
        constrained = llm.get("constrained_output_engine", "pydantic")
        if not isinstance(timeout_s, int) or timeout_s <= 0:
            raise ValueError("llm.timeout_seconds must be a positive integer")
        if not isinstance(retries, int) or retries < 0:
            raise ValueError("llm.max_retries must be a non-negative integer")
        if not isinstance(max_steps, int) or max_steps <= 0:
            raise ValueError("llm.max_steps must be a positive integer")
        if constrained not in ALLOWED_CONSTRAINED_ENGINES:
            raise ValueError(
                f"llm.constrained_output_engine must be one of {sorted(ALLOWED_CONSTRAINED_ENGINES)}"
            )


def load_config(config_path: Path | None = None, policy_pack: str | None = None) -> dict[str, Any]:
    config = _deep_merge({}, DEFAULT_CONFIG)

    path = config_path or Path("sheetproof.yml")
    if path.exists():
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ValueError("Config file must contain a mapping at top-level")
        config = _deep_merge(config, loaded)

    if policy_pack:
        packs = config.get("policy_packs", {})
        selected = packs.get(policy_pack)
        if not selected:
            raise ValueError(
                f"Unknown policy pack `{policy_pack}`. Available: {', '.join(sorted(packs.keys()))}"
            )
        config = _deep_merge(config, selected)

    _validate_config(config)
    return config
