from __future__ import annotations

import re

# Covers references like A1, $A$1, Sheet1!A1, 'Input Sheet'!$B$7, A1:B9.
REFERENCE_RE = re.compile(
    r"(?:(?:'[^']+'|[A-Za-z0-9_]+)!)?\$?[A-Z]{1,3}\$?\d+(?::\$?[A-Z]{1,3}\$?\d+)?"
)


def extract_references(formula: str) -> list[str]:
    refs = REFERENCE_RE.findall(formula)
    return sorted(set(refs))


def uses_external_reference(formula: str) -> bool:
    # Excel external refs often include bracketed workbook names.
    return "[" in formula and "]" in formula


def uses_cross_sheet_reference(formula: str) -> bool:
    return "!" in formula
