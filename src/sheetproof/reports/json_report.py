from __future__ import annotations

import json
from pathlib import Path

from sheetproof.assumptions.detector import Assumption
from sheetproof.formulas.extractor import FormulaRecord
from sheetproof.risk.findings import Finding
from sheetproof.workbook.models import WorkbookIndex


def write_json_report(
    index: WorkbookIndex,
    formulas: list[FormulaRecord],
    findings: list[Finding],
    assumptions: list[Assumption],
    out_dir: Path,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "sheetproof-report.json"

    payload = {
        "workbook": {
            "name": index.workbook,
            "path": index.workbook_path,
            "sheet_count": index.sheet_count,
            "hidden_sheets": index.hidden_sheets,
            "very_hidden_sheets": index.very_hidden_sheets,
            "external_links": index.external_links,
        },
        "summary": {
            "formula_cells": len(formulas),
            "findings": len(findings),
            "high_risk_findings": sum(1 for f in findings if f.severity == "high"),
            "assumptions_detected": len(assumptions),
        },
        "findings": [f.to_dict() for f in findings],
        "assumptions": [a.to_dict() for a in assumptions],
        "warnings": index.warnings,
    }

    out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_file
