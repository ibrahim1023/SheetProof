from __future__ import annotations

from collections import defaultdict

from sheetproof.risk.findings import Finding

WEIGHTS = {
    "formula_inconsistency": 0.25,
    "dependency_impact": 0.20,
    "hidden_or_external": 0.15,
    "hardcoded_override": 0.15,
    "version_change": 0.15,
    "volatility_or_broken_reference": 0.10,
}


TYPE_TO_BUCKET = {
    "formula_inconsistency": "formula_inconsistency",
    "hidden_sheet_dependency": "hidden_or_external",
    "external_reference": "hidden_or_external",
    "hardcoded_override": "hardcoded_override",
    "volatile_formula": "volatility_or_broken_reference",
    "broken_reference": "volatility_or_broken_reference",
}


def score_findings(findings: list[Finding], impact: dict[str, int]) -> list[Finding]:
    if not findings:
        return findings

    max_impact = max(impact.values()) if impact else 0

    for f in findings:
        key = f"{f.sheet}!{f.cell}"
        dep_score = (impact.get(key, 0) / max_impact) if max_impact else 0.0

        components = defaultdict(float)
        bucket = TYPE_TO_BUCKET.get(f.type)
        if bucket:
            components[bucket] = 1.0
        components["dependency_impact"] = dep_score

        score = 0.0
        for k, w in WEIGHTS.items():
            score += w * components[k]
        f.risk_score = round(score, 4)

        if f.risk_score >= 0.75:
            f.severity = "high"
        elif f.risk_score >= 0.45:
            f.severity = "medium"
        else:
            f.severity = "low"

    return findings
