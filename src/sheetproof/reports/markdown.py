from __future__ import annotations

from pathlib import Path

from sheetproof.assumptions.detector import Assumption
from sheetproof.risk.findings import Finding
from sheetproof.workbook.models import WorkbookIndex


def write_markdown_report(
    index: WorkbookIndex,
    findings: list[Finding],
    assumptions: list[Assumption],
    out_dir: Path,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "sheetproof-report.md"

    high = [f for f in findings if f.severity == "high"]

    lines = [
        "# SheetProof Audit Report",
        "",
        "## Executive Summary",
        f"- Workbook: `{index.workbook}`",
        f"- Sheets: {index.sheet_count}",
        f"- Findings: {len(findings)}",
        f"- High-risk findings: {len(high)}",
        f"- Assumptions detected: {len(assumptions)}",
        "",
        "## Workbook Overview",
        f"- Hidden sheets: {', '.join(index.hidden_sheets) if index.hidden_sheets else 'None'}",
        f"- Very hidden sheets: {', '.join(index.very_hidden_sheets) if index.very_hidden_sheets else 'None'}",
        f"- External links: {', '.join(index.external_links) if index.external_links else 'None'}",
        f"- Attestation status: {index.attestation_status}",
        f"- Unsupported warning codes: {', '.join(index.warning_codes) if index.warning_codes else 'None'}",
        "",
        "## High-Risk Findings",
    ]

    if high:
        for f in high:
            lines.append(f"- `{f.sheet}!{f.cell}` [{f.type}] {f.title} (score={f.risk_score})")
    else:
        lines.append("- None")

    lines.extend(["", "## Assumption Register", "| Sheet | Cell | Label | Value |", "|---|---|---|---|"])
    for a in assumptions:
        lines.append(f"| {a.sheet} | {a.cell} | {a.label} | {a.value} |")
    if not assumptions:
        lines.append("| - | - | - | - |")

    lines.extend(
        [
            "",
            "## Human Review Checklist",
            "- Verify all high-risk findings.",
            "- Review hidden/very hidden sheet dependencies.",
            "- Confirm assumption values and ownership.",
            "- Validate external workbook reference trustworthiness.",
            "",
            "## Lineage Evidence for High-Risk Findings",
        ]
    )

    if high:
        for f in high:
            lines.append(
                f"- `{f.sheet}!{f.cell}` path: "
                f"{' -> '.join(f.dependency_path) if f.dependency_path else 'N/A'} | "
                f"sources: {', '.join(f.source_cells) if f.source_cells else 'None'} | "
                f"impacted outputs: {', '.join(f.impacted_outputs) if f.impacted_outputs else 'None'}"
            )
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Evidence Appendix",
        ]
    )

    for f in findings:
        lines.append(
            f"- `{f.sheet}!{f.cell}` {f.type}: {f.deterministic_reason} | evidence={f.evidence}"
        )

    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_file
