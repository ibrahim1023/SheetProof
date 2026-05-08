from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import asdict, dataclass

from sheetproof.assumptions.labels import classify_assumption_label, is_assumption_label
from sheetproof.graph.builder import DependencyGraph
from sheetproof.workbook.models import WorkbookIndex


@dataclass
class Assumption:
    sheet: str
    cell: str
    label: str
    value: str
    downstream_cells: list[str]
    changed_from_previous_version: bool = False
    confidence: str = "medium"
    category: str = "other"

    def to_dict(self) -> dict:
        return asdict(self)


def _cell_parts(cell: str) -> tuple[str, int]:
    col = "".join(ch for ch in cell if ch.isalpha())
    row = int("".join(ch for ch in cell if ch.isdigit()))
    return col, row


def _col_to_num(col: str) -> int:
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n


def _nearest_label(
    text_cells: dict[tuple[int, int], str], row: int, col_num: int
) -> tuple[str | None, str]:
    # High confidence: first column same row.
    label = text_cells.get((row, 1))
    if label and is_assumption_label(label):
        return label, "high"

    # Medium confidence: nearest text on the left in same row.
    for c in range(col_num - 1, 0, -1):
        txt = text_cells.get((row, c))
        if txt and is_assumption_label(txt):
            return txt, "medium"

    # Low confidence: same column upward scan.
    for r in range(row - 1, 0, -1):
        txt = text_cells.get((r, col_num))
        if txt and is_assumption_label(txt):
            return txt, "low"

    return None, "low"


def _top_impacted_outputs(graph: DependencyGraph, start: str, k: int = 3) -> list[str]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    for e in graph.edges:
        adjacency[e.source].append(e.target)

    visited = set()
    q = deque([start])
    while q:
        cur = q.popleft()
        for nxt in adjacency.get(cur, []):
            if nxt in visited:
                continue
            visited.add(nxt)
            q.append(nxt)

    sinks = [node for node in visited if len(adjacency.get(node, [])) == 0]
    return sorted(sinks)[:k]


def detect_assumptions(
    index: WorkbookIndex,
    impact: dict[str, int],
    graph: DependencyGraph | None = None,
) -> list[Assumption]:
    assumptions: list[Assumption] = []

    for sheet in index.sheets:
        text_cells: dict[tuple[int, int], str] = {}
        numeric_cells: list[tuple[str, int, int, float]] = []

        for c in sheet.cells:
            if c.formula:
                continue
            col, row = _cell_parts(c.cell)
            col_num = _col_to_num(col)
            if isinstance(c.value, str):
                text_cells[(row, col_num)] = c.value.strip()
            elif isinstance(c.value, (int, float)):
                numeric_cells.append((c.cell, row, col_num, float(c.value)))

        for cell, row, col_num, value in numeric_cells:
            label, confidence = _nearest_label(text_cells, row, col_num)
            if not label:
                continue
            key = f"{sheet.name}!{cell}"
            downstream = []
            if graph is not None:
                downstream = _top_impacted_outputs(graph, key)
            if not downstream:
                downstream = [f"impact_nodes={impact.get(key, 0)}"]

            assumptions.append(
                Assumption(
                    sheet=sheet.name,
                    cell=cell,
                    label=label,
                    value=str(value).rstrip("0").rstrip(".") if "." in str(value) else str(value),
                    downstream_cells=downstream,
                    confidence=confidence,
                    category=classify_assumption_label(label),
                )
            )

    # Stable ordering
    return sorted(assumptions, key=lambda a: (a.sheet, a.cell, a.label))
