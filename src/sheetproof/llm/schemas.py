from __future__ import annotations

from pydantic import BaseModel, Field


class ExplanationCitation(BaseModel):
    cell: str = Field(min_length=2)
    reason: str = Field(min_length=1)


class StructuredExplanation(BaseModel):
    summary: str = Field(min_length=5)
    risks: list[str] = Field(default_factory=list)
    reviewer_actions: list[str] = Field(default_factory=list)
    citations: list[ExplanationCitation] = Field(default_factory=list)
