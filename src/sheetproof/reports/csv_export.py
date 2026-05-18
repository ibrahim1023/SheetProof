from __future__ import annotations

from pathlib import Path

from sheetproof.assumptions.detector import Assumption
from sheetproof.reproducibility import write_stable_csv
from sheetproof.risk.findings import Finding


def write_risk_cells_csv(findings: list[Finding], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "risk-cells.csv"
    rows = [
        [
            "Type",
            "Severity",
            "Sheet",
            "Cell",
            "Title",
            "RiskScore",
            "Reason",
            "SourceCells",
            "DependencyPath",
            "ImpactedOutputs",
            "PathDepth",
        ]
    ]
    for item in sorted(findings, key=lambda x: (x.sheet, x.cell, x.type)):
        rows.append(
            [
                item.type,
                item.severity,
                item.sheet,
                item.cell,
                item.title,
                str(item.risk_score),
                item.deterministic_reason,
                ";".join(item.source_cells),
                " -> ".join(item.dependency_path),
                ";".join(item.impacted_outputs),
                str(item.path_depth),
            ]
        )
    write_stable_csv(out_file, rows)
    return out_file


def write_assumption_register_csv(assumptions: list[Assumption], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "assumption-register.csv"
    rows = [["Sheet", "Cell", "Label", "Value", "DownstreamImpact", "ChangedFromPrevious"]]
    for a in sorted(assumptions, key=lambda x: (x.sheet, x.cell, x.label)):
        rows.append(
            [
                a.sheet,
                a.cell,
                a.label,
                str(a.value),
                ";".join(a.downstream_cells),
                str(a.changed_from_previous_version),
            ]
        )
    write_stable_csv(out_file, rows)
    return out_file
