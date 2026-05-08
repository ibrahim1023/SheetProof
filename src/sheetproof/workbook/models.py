from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass
class CellRecord:
    sheet: str
    cell: str
    value: Any
    formula: str | None
    comment: str | None


@dataclass
class SheetIndex:
    name: str
    visibility: str
    max_row: int
    max_column: int
    populated_cells: int
    formula_cells: int
    comment_cells: int
    merged_ranges: list[str]
    cells: list[CellRecord]


@dataclass
class WorkbookIndex:
    workbook: str
    workbook_path: str
    generated_at_utc: str | None
    sheet_count: int
    sheet_names: list[str]
    hidden_sheets: list[str]
    very_hidden_sheets: list[str]
    defined_names: list[str]
    external_links: list[str]
    metadata: dict[str, Any]
    sheets: list[SheetIndex]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
