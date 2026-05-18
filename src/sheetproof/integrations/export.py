from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sheetproof.reproducibility import write_stable_json


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def export_ci_annotations(report_json: Path, out_path: Path) -> Path:
    report = _load_json(report_json)
    findings = report.get("findings", [])
    annotations = []
    for f in findings:
        annotations.append(
            {
                "title": f"{f.get('type')} {f.get('sheet')}!{f.get('cell')}",
                "message": f.get("deterministic_reason", ""),
                "severity": f.get("severity", "low"),
                "evidence_pointer": f"id={f.get('id')}",
            }
        )
    return write_stable_json(out_path, {"profile": "ci_annotations_v1", "annotations": annotations})


def export_ticket_payload(report_json: Path, out_path: Path) -> Path:
    report = _load_json(report_json)
    findings = report.get("findings", [])
    tickets = []
    for f in findings:
        tickets.append(
            {
                "ticket_key": f"{f.get('sheet')}!{f.get('cell')}",
                "summary": f.get("title", ""),
                "description": f.get("deterministic_reason", ""),
                "priority": f.get("severity", "low"),
                "links": {
                    "evidence_pointer": f"id={f.get('id')}",
                },
            }
        )
    return write_stable_json(out_path, {"profile": "ticket_export_v1", "tickets": tickets})
