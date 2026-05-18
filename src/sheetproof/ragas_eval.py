from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sheetproof.reproducibility import write_stable_json


def run_ragas_eval(dataset_path: Path, output_path: Path) -> dict[str, Any]:
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = dataset.get("cases", [])
    applicable = [
        c
        for c in cases
        if c.get("question") and c.get("answer") and isinstance(c.get("contexts"), list)
    ]

    if not applicable:
        payload = {
            "status": "not_applicable",
            "reason": "No retrieval-style cases (question/answer/contexts) found in dataset.",
            "total_cases": len(cases),
            "applicable_cases": 0,
        }
        write_stable_json(output_path, payload)
        return payload

    try:
        from datasets import Dataset  # type: ignore[import-untyped]
        from ragas import evaluate  # type: ignore[import-not-found,import-untyped]
        from ragas.metrics import (  # type: ignore[import-not-found,import-untyped]
            answer_relevancy,
            context_precision,
        )
    except Exception as exc:  # noqa: BLE001
        payload = {
            "status": "unavailable",
            "reason": f"Ragas runtime unavailable: {exc}",
            "total_cases": len(cases),
            "applicable_cases": len(applicable),
        }
        write_stable_json(output_path, payload)
        return payload

    ragas_ds = Dataset.from_list(
        [
            {
                "question": c["question"],
                "answer": c["answer"],
                "contexts": c["contexts"],
                "ground_truth": c.get("ground_truth", ""),
            }
            for c in applicable
        ]
    )
    result = evaluate(dataset=ragas_ds, metrics=[answer_relevancy, context_precision])
    result_dict = dict(result)
    payload = {
        "status": "ok",
        "total_cases": len(cases),
        "applicable_cases": len(applicable),
        "metrics": result_dict,
    }
    write_stable_json(output_path, payload)
    return payload
