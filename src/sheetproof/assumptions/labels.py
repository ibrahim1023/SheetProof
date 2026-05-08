from __future__ import annotations

ASSUMPTION_KEYWORDS = {
    "growth": "growth",
    "discount": "discount",
    "tax": "tax",
    "churn": "churn",
    "price": "pricing",
    "pricing": "pricing",
    "margin": "margin",
    "headcount": "headcount",
    "conversion": "conversion",
    "adjustment": "adjustment",
    "rate": "rate",
}


def is_assumption_label(text: str) -> bool:
    low = text.lower()
    return any(keyword in low for keyword in ASSUMPTION_KEYWORDS)


def classify_assumption_label(text: str) -> str:
    low = text.lower()
    for keyword, category in ASSUMPTION_KEYWORDS.items():
        if keyword in low:
            return category
    return "other"
