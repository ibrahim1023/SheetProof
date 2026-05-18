from __future__ import annotations

from pathlib import Path
from typing import Any

from sheetproof.reproducibility import write_stable_json


def write_approval_trail(
    out_dir: Path,
    *,
    request_id: str,
    mode: str,
    approved_by: str,
    approval_reason: str,
    policy_context: dict[str, Any] | None = None,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "approval-trail.json"
    payload = {
        "request_id": request_id,
        "mode": mode,
        "approved_by": approved_by,
        "approval_reason": approval_reason,
        "policy_context": policy_context or {},
    }
    write_stable_json(out_file, payload)
    return out_file
