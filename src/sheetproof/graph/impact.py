from __future__ import annotations

from collections import defaultdict, deque

from sheetproof.graph.builder import DependencyGraph


def compute_downstream_impact(graph: DependencyGraph) -> dict[str, int]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    for e in graph.edges:
        adjacency[e.source].append(e.target)

    impact: dict[str, int] = {}
    for node in graph.nodes:
        visited: set[str] = set()
        queue = deque([node])
        while queue:
            current = queue.popleft()
            for nxt in adjacency.get(current, []):
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
        impact[node] = len(visited)

    return impact
