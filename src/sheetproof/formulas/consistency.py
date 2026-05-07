from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from sheetproof.formulas.extractor import FormulaRecord


@dataclass
class ConsistencyIssue:
    sheet: str
    cell: str
    issue_type: str
    reason: str
    expected_pattern: str | None = None


def detect_formula_consistency_issues(inventory: list[FormulaRecord]) -> list[ConsistencyIssue]:
    issues: list[ConsistencyIssue] = []
    by_sheet_row: dict[tuple[str, str], list[FormulaRecord]] = {}

    for item in inventory:
        row_num = "".join(ch for ch in item.cell if ch.isdigit())
        by_sheet_row.setdefault((item.sheet, row_num), []).append(item)

    for (sheet, _row), row_items in by_sheet_row.items():
        if len(row_items) < 3:
            continue
        formulas = [r.formula for r in row_items]
        counts = Counter(formulas)
        expected, expected_count = counts.most_common(1)[0]
        if expected_count == len(row_items):
            continue
        for item in row_items:
            if item.formula != expected:
                issues.append(
                    ConsistencyIssue(
                        sheet=sheet,
                        cell=item.cell,
                        issue_type="formula_inconsistency",
                        reason="Formula differs from dominant row pattern",
                        expected_pattern=expected,
                    )
                )

    return sorted(issues, key=lambda x: (x.sheet, x.cell))
