from __future__ import annotations

from typing import Any

from openpyxl.workbook.workbook import Workbook


def extract_workbook_metadata(workbook: Workbook) -> dict[str, Any]:
    props = workbook.properties
    return {
        "creator": props.creator,
        "last_modified_by": props.lastModifiedBy,
        "title": props.title,
        "subject": props.subject,
        "description": props.description,
        "category": props.category,
        "keywords": props.keywords,
        "created": props.created.isoformat() if props.created else None,
        "modified": props.modified.isoformat() if props.modified else None,
    }
