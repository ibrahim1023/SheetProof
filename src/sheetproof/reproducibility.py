from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


def stable_json_dumps(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_stable_json(path: Path, payload: Any) -> Path:
    path.write_text(stable_json_dumps(payload), encoding="utf-8")
    return path


def write_stable_csv(path: Path, rows: list[list[Any]]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        for row in rows:
            writer.writerow(row)
    return path


def canonicalize_for_hash(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k in sorted(value.keys()):
            if k == "generated_at_utc":
                continue
            out[k] = canonicalize_for_hash(value[k])
        return out
    if isinstance(value, list):
        return [canonicalize_for_hash(v) for v in value]
    if isinstance(value, float):
        return round(value, 6)
    return value


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
