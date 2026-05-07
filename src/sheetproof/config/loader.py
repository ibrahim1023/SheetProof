from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sheetproof.config.defaults import DEFAULT_CONFIG


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    path = config_path or Path("sheetproof.yml")
    if not path.exists():
        return config

    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        return config
    return _deep_merge(config, loaded)
