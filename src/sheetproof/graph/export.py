from __future__ import annotations

from pathlib import Path

from sheetproof.graph.builder import DependencyGraph
from sheetproof.reproducibility import write_stable_json


def write_dependency_graph(graph: DependencyGraph, impact: dict[str, int], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "dependency-graph.json"
    payload = graph.to_dict()
    payload["impact"] = dict(sorted(impact.items()))
    write_stable_json(out_file, payload)
    return out_file
