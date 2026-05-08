from __future__ import annotations

import json
from pathlib import Path

from sheetproof.reproducibility import canonicalize_for_hash, sha256_file, sha256_text, write_stable_json


ARTIFACT_FILES = [
    "workbook-index.json",
    "formula-map.json",
    "dependency-graph.json",
    "sheetproof-report.json",
    "sheetproof-report.md",
    "risk-cells.csv",
    "assumption-register.csv",
]


def _canonical_hash_for_json(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    canonical = canonicalize_for_hash(payload)
    text = json.dumps(canonical, sort_keys=True, ensure_ascii=False)
    return sha256_text(text)


def write_reproducibility_manifest(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for name in ARTIFACT_FILES:
        p = out_dir / name
        if not p.exists():
            continue
        if p.suffix == ".json":
            canonical_hash = _canonical_hash_for_json(p)
        else:
            canonical_hash = sha256_file(p)
        files.append(
            {
                "file": name,
                "sha256": sha256_file(p),
                "canonical_sha256": canonical_hash,
            }
        )

    payload = {"artifacts": sorted(files, key=lambda x: x["file"]) }
    out_file = out_dir / "reproducibility-manifest.json"
    write_stable_json(out_file, payload)
    return out_file
