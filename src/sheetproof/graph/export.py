from __future__ import annotations

import json
from pathlib import Path

from sheetproof.graph.builder import DependencyGraph


def write_dependency_graph(graph: DependencyGraph, impact: dict[str, int], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "dependency-graph.json"
    payload = graph.to_dict()
    payload["impact"] = impact
    out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_file
