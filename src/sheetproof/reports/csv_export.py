from __future__ import annotations

import csv
from pathlib import Path

from sheetproof.assumptions.detector import Assumption
from sheetproof.risk.findings import Finding


def write_risk_cells_csv(findings: list[Finding], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "risk-cells.csv"
    with out_file.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Type", "Severity", "Sheet", "Cell", "Title", "RiskScore", "Reason"])
        for item in findings:
            w.writerow(
                [
                    item.type,
                    item.severity,
                    item.sheet,
                    item.cell,
                    item.title,
                    item.risk_score,
                    item.deterministic_reason,
                ]
            )
    return out_file


def write_assumption_register_csv(assumptions: list[Assumption], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "assumption-register.csv"
    with out_file.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Sheet", "Cell", "Label", "Value", "DownstreamImpact", "ChangedFromPrevious"])
        for a in assumptions:
            w.writerow(
                [
                    a.sheet,
                    a.cell,
                    a.label,
                    a.value,
                    ";".join(a.downstream_cells),
                    a.changed_from_previous_version,
                ]
            )
    return out_file
