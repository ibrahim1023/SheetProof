from __future__ import annotations

from typing import Any


def build_cell_explanation_prompt(cell: str, deterministic_context: dict[str, Any]) -> str:
    workbook = deterministic_context.get("workbook", "unknown")
    finding_count = len(deterministic_context.get("findings", []))
    formula = deterministic_context.get("formula")
    dependencies = deterministic_context.get("dependencies", [])

    lines = [
        "You are an explanation assistant for spreadsheet audit outputs.",
        "Use only the provided deterministic evidence. Do not invent cells, formulas, or risks.",
        f"Workbook: {workbook}",
        f"Target cell: {cell}",
        f"Formula: {formula if formula else 'N/A'}",
        f"Related findings count: {finding_count}",
        f"Dependencies: {', '.join(dependencies) if dependencies else 'None'}",
        "",
        "Write a concise explanation with:",
        "1) what the cell does",
        "2) what risks are attached (if any)",
        "3) what a reviewer should verify next",
    ]
    return "\n".join(lines)
