from __future__ import annotations

from dataclasses import asdict, dataclass

from sheetproof.formulas.extractor import FormulaRecord


@dataclass
class DependencyEdge:
    source: str
    target: str


@dataclass
class DependencyGraph:
    nodes: list[str]
    edges: list[DependencyEdge]

    def to_dict(self) -> dict:
        return {
            "nodes": self.nodes,
            "edges": [asdict(e) for e in self.edges],
        }


def build_dependency_graph(inventory: list[FormulaRecord]) -> DependencyGraph:
    nodes: set[str] = set()
    edges: list[DependencyEdge] = []

    for f in inventory:
        formula_cell = f"{f.sheet}!{f.cell}"
        nodes.add(formula_cell)

        for ref in f.references:
            if "!" in ref:
                source = ref
            else:
                source = f"{f.sheet}!{ref}"
            nodes.add(source)
            edges.append(DependencyEdge(source=source, target=formula_cell))

    return DependencyGraph(nodes=sorted(nodes), edges=edges)
