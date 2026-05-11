from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Finding:
    id: str
    type: str
    severity: str
    sheet: str
    cell: str
    title: str
    deterministic_reason: str
    evidence: dict[str, Any]
    risk_score: float = 0.0
    requires_human_review: bool = True
    source_cells: list[str] = field(default_factory=list)
    dependency_path: list[str] = field(default_factory=list)
    impacted_outputs: list[str] = field(default_factory=list)
    path_depth: int = 0
    source: str = "deterministic"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
