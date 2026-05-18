from __future__ import annotations

from pathlib import Path

from sheetproof.reproducibility import write_stable_json

WARNING_TAXONOMY: dict[str, str] = {
    "UNSUPPORTED:VBA_MACROS": "Workbook contains VBA macros (vbaProject.bin).",
    "UNSUPPORTED:PIVOT_TABLES": "Workbook contains pivot table definitions.",
    "UNSUPPORTED:DATA_CONNECTIONS": "Workbook contains external data connections.",
    "UNSUPPORTED:SLICERS": "Workbook contains slicers.",
    "UNSUPPORTED:PACKAGE_READ_ERROR": "Workbook package could not be fully inspected.",
}

COVERAGE_MATRIX: list[dict[str, str]] = [
    {"feature": "formulas", "status": "supported", "attestation": "full"},
    {"feature": "worksheet_visibility", "status": "supported", "attestation": "full"},
    {"feature": "external_links", "status": "supported", "attestation": "full"},
    {"feature": "named_ranges", "status": "supported", "attestation": "full"},
    {"feature": "merged_cells", "status": "supported", "attestation": "full"},
    {"feature": "vba_macros", "status": "unsupported", "attestation": "cannot_attest"},
    {"feature": "pivot_tables", "status": "unsupported", "attestation": "cannot_attest"},
    {"feature": "data_connections", "status": "unsupported", "attestation": "cannot_attest"},
    {"feature": "slicers", "status": "unsupported", "attestation": "cannot_attest"},
]


def write_coverage_matrix(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "coverage-matrix.json"
    write_stable_json(
        out,
        {
            "version": 1,
            "features": COVERAGE_MATRIX,
            "warning_taxonomy": WARNING_TAXONOMY,
        },
    )
    return out
