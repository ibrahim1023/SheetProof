from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sheetproof.formulas.references import (
    extract_references,
    uses_cross_sheet_reference,
    uses_external_reference,
)
from sheetproof.reproducibility import write_stable_json
from sheetproof.formulas.volatility import find_volatile_functions
from sheetproof.workbook.models import WorkbookIndex


@dataclass
class FormulaRecord:
    sheet: str
    cell: str
    formula: str
    category: str
    references: list[str]
    uses_cross_sheet_reference: bool
    uses_external_reference: bool
    uses_volatile_function: bool
    volatile_functions: list[str]
    nearby_label: str | None


FORMULA_CATEGORY_KEYWORDS = {
    "aggregation": ["SUM(", "AVERAGE(", "MIN(", "MAX("],
    "conditional": ["IF(", "IFS(", "SWITCH("],
    "lookup": ["VLOOKUP(", "XLOOKUP(", "INDEX(", "MATCH("],
}


def _categorize_formula(formula: str) -> str:
    upper = formula.upper()
    for category, keys in FORMULA_CATEGORY_KEYWORDS.items():
        if any(k in upper for k in keys):
            return category
    return "other"


def extract_formula_inventory(index: WorkbookIndex) -> list[FormulaRecord]:
    inventory: list[FormulaRecord] = []

    for sheet in index.sheets:
        labels_by_row: dict[int, str] = {}
        for c in sheet.cells:
            if c.formula is None and isinstance(c.value, str) and c.cell.startswith("A"):
                row = int("".join(ch for ch in c.cell if ch.isdigit()))
                labels_by_row[row] = c.value.strip()

        for c in sheet.cells:
            if not c.formula:
                continue
            row = int("".join(ch for ch in c.cell if ch.isdigit()))
            volatile_functions = find_volatile_functions(c.formula)
            inventory.append(
                FormulaRecord(
                    sheet=sheet.name,
                    cell=c.cell,
                    formula=c.formula,
                    category=_categorize_formula(c.formula),
                    references=extract_references(c.formula),
                    uses_cross_sheet_reference=uses_cross_sheet_reference(c.formula),
                    uses_external_reference=uses_external_reference(c.formula),
                    uses_volatile_function=bool(volatile_functions),
                    volatile_functions=volatile_functions,
                    nearby_label=labels_by_row.get(row),
                )
            )

    return sorted(inventory, key=lambda x: (x.sheet, x.cell))


def formula_inventory_to_json_records(inventory: list[FormulaRecord]) -> list[dict[str, Any]]:
    return [asdict(item) for item in inventory]


def write_formula_map(inventory: list[FormulaRecord], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "formula-map.json"
    write_stable_json(out_file, formula_inventory_to_json_records(inventory))
    return out_file
