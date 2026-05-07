from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sheetproof.config.loader import load_config
from sheetproof.diff.cell_diff import CellChange, diff_cells
from sheetproof.diff.formula_diff import summarize_formula_diffs
from sheetproof.workbook.models import WorkbookIndex
from sheetproof.workbook.parser import parse_workbook


@dataclass
class WorkbookDiffResult:
    old_workbook: str
    new_workbook: str
    changed_formulas: int
    changed_values: int
    changed_assumptions: int
    new_formulas: int
    deleted_formulas: int
    renamed_sheets: list[dict[str, str]]
    newly_hidden_sheets: list[str]
    new_external_references: list[str]
    high_risk_changed_cells: int
    changes: list[CellChange]

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["changes"] = [c.to_dict() for c in self.changes]
        return out


def _detect_renamed_sheets(old_index: WorkbookIndex, new_index: WorkbookIndex) -> list[dict[str, str]]:
    # Conservative placeholder: explicit rename detection is hard without workbook history.
    # We expose empty list for now and rely on added/removed sheets via cell-level changes.
    _ = old_index
    _ = new_index
    return []


def compute_workbook_diff(old_path: Path, new_path: Path) -> WorkbookDiffResult:
    cfg = load_config()
    high_risk_sheets = cfg.get("risk", {}).get("high_risk_sheets", [])

    old_index = parse_workbook(old_path)
    new_index = parse_workbook(new_path)

    changes = diff_cells(old_index, new_index, high_risk_sheets)
    formula_summary = summarize_formula_diffs(changes)

    old_hidden = set(old_index.hidden_sheets + old_index.very_hidden_sheets)
    new_hidden = set(new_index.hidden_sheets + new_index.very_hidden_sheets)

    return WorkbookDiffResult(
        old_workbook=old_index.workbook,
        new_workbook=new_index.workbook,
        changed_formulas=formula_summary["changed_formulas"],
        changed_values=sum(1 for c in changes if c.change_type == "value_changed"),
        changed_assumptions=sum(1 for c in changes if "assumption_changed" in c.reasons),
        new_formulas=formula_summary["new_formulas"],
        deleted_formulas=formula_summary["deleted_formulas"],
        renamed_sheets=_detect_renamed_sheets(old_index, new_index),
        newly_hidden_sheets=sorted(list(new_hidden - old_hidden)),
        new_external_references=sorted(list(set(new_index.external_links) - set(old_index.external_links))),
        high_risk_changed_cells=sum(1 for c in changes if c.high_risk),
        changes=changes,
    )


def write_workbook_diff(result: WorkbookDiffResult, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "workbook-diff.json"
    out_file.write_text(json.dumps(result.to_dict(), indent=2, default=str), encoding="utf-8")
    return out_file


def render_diff_summary(result: WorkbookDiffResult) -> str:
    lines = [
        f"Changed formulas: {result.changed_formulas}",
        f"Changed values: {result.changed_values}",
        f"Changed assumptions: {result.changed_assumptions}",
        f"New formulas: {result.new_formulas}",
        f"Deleted formulas: {result.deleted_formulas}",
        f"Renamed sheets: {len(result.renamed_sheets)}",
        f"Newly hidden sheets: {len(result.newly_hidden_sheets)}",
        f"New external references: {len(result.new_external_references)}",
        f"High-risk changed cells: {result.high_risk_changed_cells}",
    ]
    return "\n".join(lines)
