from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sheetproof.assumptions.detector import Assumption, detect_assumptions
from sheetproof.config.loader import load_config
from sheetproof.diff.cell_diff import CellChange, diff_cells
from sheetproof.diff.formula_diff import summarize_formula_diffs
from sheetproof.formulas.extractor import extract_formula_inventory
from sheetproof.graph.builder import build_dependency_graph
from sheetproof.graph.impact import compute_downstream_impact
from sheetproof.reproducibility import write_stable_json
from sheetproof.workbook.models import WorkbookIndex
from sheetproof.workbook.parser import parse_workbook


@dataclass
class AssumptionDelta:
    sheet: str
    cell: str
    label: str
    old_value: str
    new_value: str
    absolute_change: float | None
    percent_change: float | None
    downstream_cells: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
    assumption_deltas: list[AssumptionDelta]

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["changes"] = [c.to_dict() for c in self.changes]
        out["assumption_deltas"] = [a.to_dict() for a in self.assumption_deltas]
        return out


def _detect_renamed_sheets(old_index: WorkbookIndex, new_index: WorkbookIndex) -> list[dict[str, str]]:
    _ = old_index
    _ = new_index
    return []


def _to_float(v: str) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _assumption_key(a: Assumption) -> tuple[str, str, str]:
    return (a.sheet, a.cell, a.label)


def _compute_assumption_deltas(old_assumptions: list[Assumption], new_assumptions: list[Assumption]) -> list[AssumptionDelta]:
    old_map = {_assumption_key(a): a for a in old_assumptions}
    new_map = {_assumption_key(a): a for a in new_assumptions}

    deltas: list[AssumptionDelta] = []
    for key in sorted(set(old_map.keys()) & set(new_map.keys())):
        old_a = old_map[key]
        new_a = new_map[key]
        if old_a.value == new_a.value:
            continue

        old_f = _to_float(old_a.value)
        new_f = _to_float(new_a.value)
        absolute_change = None
        percent_change = None
        if old_f is not None and new_f is not None:
            absolute_change = round(new_f - old_f, 6)
            if old_f != 0:
                percent_change = round(((new_f - old_f) / abs(old_f)) * 100, 6)

        deltas.append(
            AssumptionDelta(
                sheet=new_a.sheet,
                cell=new_a.cell,
                label=new_a.label,
                old_value=old_a.value,
                new_value=new_a.value,
                absolute_change=absolute_change,
                percent_change=percent_change,
                downstream_cells=new_a.downstream_cells,
            )
        )

    return deltas


def compute_workbook_diff(
    old_path: Path,
    new_path: Path,
    policy_pack: str | None = None,
) -> WorkbookDiffResult:
    cfg = load_config(policy_pack=policy_pack)
    high_risk_sheets = cfg.get("risk", {}).get("high_risk_sheets", [])

    old_index = parse_workbook(old_path)
    new_index = parse_workbook(new_path)

    changes = diff_cells(old_index, new_index, high_risk_sheets)
    formula_summary = summarize_formula_diffs(changes)

    old_hidden = set(old_index.hidden_sheets + old_index.very_hidden_sheets)
    new_hidden = set(new_index.hidden_sheets + new_index.very_hidden_sheets)

    old_inv = extract_formula_inventory(old_index)
    new_inv = extract_formula_inventory(new_index)
    old_graph = build_dependency_graph(old_inv)
    new_graph = build_dependency_graph(new_inv)
    old_impact = compute_downstream_impact(old_graph)
    new_impact = compute_downstream_impact(new_graph)
    old_assumptions = detect_assumptions(old_index, old_impact, old_graph)
    new_assumptions = detect_assumptions(new_index, new_impact, new_graph)
    assumption_deltas = _compute_assumption_deltas(old_assumptions, new_assumptions)

    return WorkbookDiffResult(
        old_workbook=old_index.workbook,
        new_workbook=new_index.workbook,
        changed_formulas=formula_summary["changed_formulas"],
        changed_values=sum(1 for c in changes if c.change_type == "value_changed"),
        changed_assumptions=len(assumption_deltas),
        new_formulas=formula_summary["new_formulas"],
        deleted_formulas=formula_summary["deleted_formulas"],
        renamed_sheets=_detect_renamed_sheets(old_index, new_index),
        newly_hidden_sheets=sorted(list(new_hidden - old_hidden)),
        new_external_references=sorted(list(set(new_index.external_links) - set(old_index.external_links))),
        high_risk_changed_cells=sum(1 for c in changes if c.high_risk),
        changes=changes,
        assumption_deltas=assumption_deltas,
    )


def write_workbook_diff(result: WorkbookDiffResult, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "workbook-diff.json"
    write_stable_json(out_file, result.to_dict())

    assumption_diff_path = out_dir / "assumption-diff.json"
    write_stable_json(
        assumption_diff_path,
        {"assumption_deltas": [a.to_dict() for a in result.assumption_deltas]},
    )
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
