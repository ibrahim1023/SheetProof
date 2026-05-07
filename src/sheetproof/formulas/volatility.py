from __future__ import annotations

VOLATILE_FUNCTIONS = {
    "NOW",
    "TODAY",
    "RAND",
    "RANDBETWEEN",
    "OFFSET",
    "INDIRECT",
    "CELL",
    "INFO",
}


def find_volatile_functions(formula: str) -> list[str]:
    upper = formula.upper()
    found = [name for name in VOLATILE_FUNCTIONS if f"{name}(" in upper]
    return sorted(found)
