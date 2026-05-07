from __future__ import annotations

ASSUMPTION_KEYWORDS = {
    "rate",
    "growth",
    "discount",
    "tax",
    "churn",
    "price",
    "margin",
    "headcount",
    "conversion",
    "adjustment",
}


def is_assumption_label(text: str) -> bool:
    low = text.lower()
    return any(keyword in low for keyword in ASSUMPTION_KEYWORDS)
