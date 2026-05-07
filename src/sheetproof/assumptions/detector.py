from __future__ import annotations

from dataclasses import asdict, dataclass

from sheetproof.assumptions.labels import is_assumption_label
from sheetproof.workbook.models import WorkbookIndex


@dataclass
class Assumption:
    sheet: str
    cell: str
    label: str
    value: str
    downstream_cells: list[str]
    changed_from_previous_version: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def detect_assumptions(index: WorkbookIndex, impact: dict[str, int]) -> list[Assumption]:
    assumptions: list[Assumption] = []

    for sheet in index.sheets:
        labels_by_row = {}
        values_by_row = {}
        for c in sheet.cells:
            if c.formula:
                continue
            row = int("".join(ch for ch in c.cell if ch.isdigit()))
            col = "".join(ch for ch in c.cell if ch.isalpha())
            if isinstance(c.value, str) and col == "A":
                labels_by_row[row] = c.value.strip()
            elif isinstance(c.value, (int, float)) and col in {"B", "C", "D"}:
                values_by_row.setdefault(row, []).append((c.cell, c.value))

        for row, label in labels_by_row.items():
            if not is_assumption_label(label):
                continue
            for cell, value in values_by_row.get(row, []):
                key = f"{sheet.name}!{cell}"
                assumptions.append(
                    Assumption(
                        sheet=sheet.name,
                        cell=cell,
                        label=label,
                        value=str(value),
                        downstream_cells=[f"impact_nodes={impact.get(key, 0)}"],
                    )
                )

    return assumptions
