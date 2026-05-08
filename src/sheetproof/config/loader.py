from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sheetproof.config.defaults import DEFAULT_CONFIG

ALLOWED_SEVERITIES = {"low", "medium", "high"}
ALLOWED_VOLATILE_MODES = {"allow", "warn", "deny"}


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
