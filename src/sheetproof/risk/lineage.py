from __future__ import annotations

from collections import defaultdict, deque

from sheetproof.graph.builder import DependencyGraph
from sheetproof.risk.findings import Finding


def _build_adjacency(graph: DependencyGraph) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    forward: dict[str, list[str]] = defaultdict(list)
    reverse: dict[str, list[str]] = defaultdict(list)
    for e in graph.edges:
        forward[e.source].append(e.target)
        reverse[e.target].append(e.source)
    return forward, reverse


def _shortest_path(forward: dict[str, list[str]], start: str, goal: str) -> list[str]:
    if start == goal:
        return [start]
    q = deque([start])
    prev: dict[str, str | None] = {start: None}
    while q:
        cur = q.popleft()
        for nxt in forward.get(cur, []):
            if nxt in prev:
                continue
            prev[nxt] = cur
            if nxt == goal:
                path = [goal]
                p = cur
                while p is not None:
                    path.append(p)
                    p = prev[p]
                return list(reversed(path))
            q.append(nxt)
    return []


def _reachable_sinks(forward: dict[str, list[str]], start: str) -> list[str]:
    visited = set()
    q = deque([start])
    sinks: set[str] = set()
    while q:
        cur = q.popleft()
        for nxt in forward.get(cur, []):
            if nxt in visited:
                continue
            visited.add(nxt)
            q.append(nxt)
    for node in visited:
        if len(forward.get(node, [])) == 0:
            sinks.add(node)
    return sorted(sinks)


def enrich_findings_with_lineage(
    findings: list[Finding], graph: DependencyGraph, impact: dict[str, int]
) -> list[Finding]:
    forward, reverse = _build_adjacency(graph)

    for f in findings:
        target = f"{f.sheet}!{f.cell}"
        source_cells = sorted(set(reverse.get(target, [])))

        dependency_path: list[str] = []
        if source_cells:
            best: list[str] | None = None
            for src in source_cells:
                path = _shortest_path(forward, src, target)
                if path and (best is None or len(path) < len(best)):
                    best = path
            dependency_path = best or [target]
        else:
            dependency_path = [target]

        impacted = _reachable_sinks(forward, target)
        impacted = sorted(impacted, key=lambda n: impact.get(n, 0), reverse=True)[:3]

        f.source_cells = source_cells
        f.dependency_path = dependency_path
        f.impacted_outputs = impacted
        f.path_depth = max(0, len(dependency_path) - 1)

        f.evidence.setdefault("lineage", {})
        f.evidence["lineage"] = {
            "source_cells": source_cells,
            "dependency_path": dependency_path,
            "impacted_outputs": impacted,
            "path_depth": f.path_depth,
        }

    return findings
