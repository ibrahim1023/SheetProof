from __future__ import annotations

from dataclasses import asdict, dataclass
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
