from pathlib import Path

import pytest

from sheetproof.config.loader import load_config


def test_observability_primary_backend_validation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = Path("sheetproof.yml")
    cfg.write_text(
        "schema_version: 1\nobservability:\n  primary_backend: invalid\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="observability.primary_backend"):
        load_config()


def test_observability_primary_backend_valid(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = Path("sheetproof.yml")
    cfg.write_text(
        "schema_version: 1\nobservability:\n  primary_backend: phoenix\n",
        encoding="utf-8",
    )
    loaded = load_config()
    assert loaded["observability"]["primary_backend"] == "phoenix"
