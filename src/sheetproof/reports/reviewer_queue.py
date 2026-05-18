from __future__ import annotations

from pathlib import Path
from typing import Any

from sheetproof.reproducibility import write_stable_json
from sheetproof.risk.findings import Finding


def write_reviewer_queue(findings: list[Finding], out_dir: Path, top_n: int = 20) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "reviewer-queue.json"
    prioritized = sorted(
        findings,
        key=lambda f: (
            0 if f.severity == "high" else 1 if f.severity == "medium" else 2,
            -float(f.risk_score),
            f.sheet,
            f.cell,
        ),
    )[:top_n]

    items: list[dict[str, Any]] = []
    for f in prioritized:
        items.append(
            {
                "id": f.id,
                "priority_reason": f"severity={f.severity}; score={f.risk_score}",
                "location": f"{f.sheet}!{f.cell}",
                "title": f.title,
                "evidence_pointer": {
                    "finding_id": f.id,
                    "source_cells": f.source_cells,
                    "dependency_path": f.dependency_path,
                },
            }
        )
    write_stable_json(out, {"items": items})
    return out
