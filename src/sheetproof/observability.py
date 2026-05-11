from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def write_trace(event: dict[str, Any], out_dir: Path = Path('.sheetproof')) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / 'traces.jsonl'
    event = dict(event)
    event.setdefault('ts_unix', time.time())
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')
    return path
