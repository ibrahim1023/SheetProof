from __future__ import annotations

from collections import Counter
from typing import Any

from sheetproof.formulas.consistency import detect_formula_consistency_issues
from sheetproof.formulas.extractor import FormulaRecord
from sheetproof.risk.findings import Finding
from sheetproof.workbook.models import WorkbookIndex

SEVERITY_SCORES = {"high": 0.85, "medium": 0.6, "low": 0.35}


def _finding_id(kind: str, sheet: str, cell: str) -> str:
    return f"{kind}:{sheet}:{cell}"


def _sev(policy: dict[str, Any] | None, finding_type: str, default: str) -> str:
    if not policy:
        return default
    return (
        policy.get("severity_overrides", {}).get(finding_type)
        or policy.get("severity_overrides", {}).get(finding_type.replace("_", "-"))
        or default
    )


def detect_formula_inconsistency_findings(
    inventory: list[FormulaRecord], risk_policy: dict[str, Any] | None = None
) -> list[Finding]:
    findings: list[Finding] = []
    sev = _sev(risk_policy, "formula_inconsistency", "high")
    for issue in detect_formula_consistency_issues(inventory):
        findings.append(
            Finding(
                id=_finding_id("formula_inconsistency", issue.sheet, issue.cell),
                type="formula_inconsistency",
                severity=sev,
                sheet=issue.sheet,
                cell=issue.cell,
                title="Formula differs from neighboring pattern",
                deterministic_reason=issue.reason,
                evidence={"expected_pattern": issue.expected_pattern},
                risk_score=SEVERITY_SCORES[sev],
            )
        )
    return findings


def detect_hidden_external_dependency_findings(
    index: WorkbookIndex,
    inventory: list[FormulaRecord],
    risk_policy: dict[str, Any] | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    hidden = set(index.hidden_sheets + index.very_hidden_sheets)
    hidden_sev = _sev(risk_policy, "hidden_sheet_dependency", "high")
    ext_sev = _sev(risk_policy, "external_reference", "high")

    for item in inventory:
        ref_hidden = [
            r for r in item.references if "!" in r and r.split("!", 1)[0].strip("'") in hidden
        ]
        if ref_hidden:
            findings.append(
                Finding(
                    id=_finding_id("hidden_sheet_dependency", item.sheet, item.cell),
                    type="hidden_sheet_dependency",
                    severity=hidden_sev,
                    sheet=item.sheet,
                    cell=item.cell,
                    title="Formula references hidden sheet",
                    deterministic_reason="Formula references hidden/very hidden sheet",
                    evidence={"hidden_references": ref_hidden},
                    risk_score=SEVERITY_SCORES[hidden_sev],
                )
            )

        if item.uses_external_reference:
            findings.append(
                Finding(
                    id=_finding_id("external_reference", item.sheet, item.cell),
                    type="external_reference",
                    severity=ext_sev,
                    sheet=item.sheet,
                    cell=item.cell,
                    title="Formula references external workbook",
                    deterministic_reason="Formula includes external workbook pattern",
                    evidence={"formula": item.formula},
                    risk_score=SEVERITY_SCORES[ext_sev],
                )
            )

    return findings


def detect_broken_reference_findings(
    inventory: list[FormulaRecord], risk_policy: dict[str, Any] | None = None
) -> list[Finding]:
    findings: list[Finding] = []
    sev = _sev(risk_policy, "broken_reference", "high")
    for item in inventory:
        if "#REF!" in item.formula.upper():
            findings.append(
                Finding(
                    id=_finding_id("broken_reference", item.sheet, item.cell),
                    type="broken_reference",
                    severity=sev,
                    sheet=item.sheet,
                    cell=item.cell,
                    title="Formula contains broken reference",
                    deterministic_reason="Formula text contains #REF!",
                    evidence={"formula": item.formula},
                    risk_score=SEVERITY_SCORES[sev],
                )
            )
    return findings


def detect_hardcoded_override_findings(
    index: WorkbookIndex, risk_policy: dict[str, Any] | None = None
) -> list[Finding]:
    findings: list[Finding] = []
    sev = _sev(risk_policy, "hardcoded_override", "medium")

    for sheet in index.sheets:
        by_row = {}
        for c in sheet.cells:
            row = int("".join(ch for ch in c.cell if ch.isdigit()))
            by_row.setdefault(row, []).append(c)

        for _row_num, row_cells in by_row.items():
            formula_count = sum(1 for c in row_cells if c.formula)
            numeric_literals = [
                c for c in row_cells if c.formula is None and isinstance(c.value, (int, float))
            ]
            if formula_count >= 2 and len(numeric_literals) == 1:
                suspect = numeric_literals[0]
                findings.append(
                    Finding(
                        id=_finding_id("hardcoded_override", sheet.name, suspect.cell),
                        type="hardcoded_override",
                        severity=sev,
                        sheet=sheet.name,
                        cell=suspect.cell,
                        title="Numeric hardcoded value inside formula region",
                        deterministic_reason="Single numeric literal found among formula cells in row",
                        evidence={"value": suspect.value, "formula_neighbors": formula_count},
                        risk_score=SEVERITY_SCORES[sev],
                    )
                )

    return findings


def detect_volatile_formula_findings(
    inventory: list[FormulaRecord], risk_policy: dict[str, Any] | None = None
) -> list[Finding]:
    findings: list[Finding] = []
    volatile_mode = (risk_policy or {}).get("volatile_mode", "warn")
    if volatile_mode == "allow":
        return findings

    default_sev = "high" if volatile_mode == "deny" else "medium"
    sev = _sev(risk_policy, "volatile_formula", default_sev)

    for item in inventory:
        if item.volatile_functions:
            findings.append(
                Finding(
                    id=_finding_id("volatile_formula", item.sheet, item.cell),
                    type="volatile_formula",
                    severity=sev,
                    sheet=item.sheet,
                    cell=item.cell,
                    title="Formula uses volatile function",
                    deterministic_reason="Volatile functions can produce unstable recalculations",
                    evidence={"volatile_functions": item.volatile_functions},
                    risk_score=SEVERITY_SCORES[sev],
                )
            )
    return findings


def dedupe_findings(findings: list[Finding]) -> list[Finding]:
    seen = set()
    out: list[Finding] = []
    for f in findings:
        key = (f.type, f.sheet, f.cell)
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def finding_type_counts(findings: list[Finding]) -> dict[str, int]:
    ctr = Counter(f.type for f in findings)
    return dict(sorted(ctr.items()))
