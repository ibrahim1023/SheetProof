from __future__ import annotations

from sheetproof.diff.cell_diff import CellChange


def summarize_formula_diffs(changes: list[CellChange]) -> dict[str, int]:
    changed_formulas = sum(1 for c in changes if c.change_type == "formula_changed")
    new_formulas = sum(
        1 for c in changes if c.change_type == "new_cell" and c.new_formula is not None
    )
    deleted_formulas = sum(
        1 for c in changes if c.change_type == "deleted_cell" and c.old_formula is not None
    )
    return {
        "changed_formulas": changed_formulas,
        "new_formulas": new_formulas,
        "deleted_formulas": deleted_formulas,
    }
