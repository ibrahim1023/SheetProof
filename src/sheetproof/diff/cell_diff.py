from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TypedDict
from typing import Any

from sheetproof.workbook.models import WorkbookIndex


@dataclass
class CellChange:
    sheet: str
    cell: str
    change_type: str
    old_value: Any
    new_value: Any
    old_formula: str | None
    new_formula: str | None
    is_assumption_like: bool
    high_risk: bool
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _assumption_like_label(label: str | None) -> bool:
    if not label:
        return False
    low = label.lower()
    keywords = [
        "rate",
        "growth",
        "discount",
        "tax",
        "churn",
        "price",
        "margin",
        "headcount",
        "conversion",
        "adjustment",
    ]
    return any(k in low for k in keywords)


def _build_cell_map(index: WorkbookIndex) -> dict[tuple[str, str], CellInfo]:
    out: dict[tuple[str, str], CellInfo] = {}
    for sheet in index.sheets:
        labels_by_row: dict[int, str] = {}
        for c in sheet.cells:
            if c.formula is None and isinstance(c.value, str) and c.cell.startswith("A"):
                row = int("".join(ch for ch in c.cell if ch.isdigit()))
                labels_by_row[row] = c.value.strip()

        for c in sheet.cells:
            row = int("".join(ch for ch in c.cell if ch.isdigit()))
            out[(sheet.name, c.cell)] = {
                "value": c.value,
                "formula": c.formula,
                "label": labels_by_row.get(row),
            }
    return out


def diff_cells(
    old_index: WorkbookIndex,
    new_index: WorkbookIndex,
    high_risk_sheets: list[str],
) -> list[CellChange]:
    old_map = _build_cell_map(old_index)
    new_map = _build_cell_map(new_index)

    all_keys = sorted(set(old_map.keys()) | set(new_map.keys()))
    changes: list[CellChange] = []

    for sheet, cell in all_keys:
        old = old_map.get((sheet, cell))
        new = new_map.get((sheet, cell))

        if old is None:
            if new is None:
                continue
            changes.append(
                CellChange(
                    sheet=sheet,
                    cell=cell,
                    change_type="new_cell",
                    old_value=None,
                    new_value=new["value"],
                    old_formula=None,
                    new_formula=new["formula"],
                    is_assumption_like=_assumption_like_label(new.get("label")),
                    high_risk=sheet in high_risk_sheets,
                    reasons=["new_cell", "high_risk_sheet"] if sheet in high_risk_sheets else ["new_cell"],
                )
            )
            continue

        if new is None:
            changes.append(
                CellChange(
                    sheet=sheet,
                    cell=cell,
                    change_type="deleted_cell",
                    old_value=old["value"],
                    new_value=None,
                    old_formula=old["formula"],
                    new_formula=None,
                    is_assumption_like=_assumption_like_label(old.get("label")),
                    high_risk=sheet in high_risk_sheets,
                    reasons=["deleted_cell", "high_risk_sheet"] if sheet in high_risk_sheets else ["deleted_cell"],
                )
            )
            continue

        if old["formula"] != new["formula"] or old["value"] != new["value"]:
            change_type = "formula_changed" if old["formula"] != new["formula"] else "value_changed"
            reasons = [change_type]
            if sheet in high_risk_sheets:
                reasons.append("high_risk_sheet")
            if "#REF!" in str(new["formula"] or "").upper():
                reasons.append("broken_reference")
            if "[" in str(new["formula"] or "") and "]" in str(new["formula"] or ""):
                reasons.append("external_reference")

            is_assumption = _assumption_like_label(new.get("label") or old.get("label"))
            if is_assumption:
                reasons.append("assumption_changed")

            high_risk = (
                sheet in high_risk_sheets
                or "broken_reference" in reasons
                or "external_reference" in reasons
                or is_assumption
            )

            changes.append(
                CellChange(
                    sheet=sheet,
                    cell=cell,
                    change_type=change_type,
                    old_value=old["value"],
                    new_value=new["value"],
                    old_formula=old["formula"],
                    new_formula=new["formula"],
                    is_assumption_like=is_assumption,
                    high_risk=high_risk,
                    reasons=reasons,
                )
            )

    return changes
class CellInfo(TypedDict):
    value: Any
    formula: str | None
    label: str | None
