from __future__ import annotations

import json
from pathlib import Path

from sheetproof.llm.schemas import StructuredExplanation
from sheetproof.reproducibility import write_stable_json


def run_explanation_eval(dataset_path: Path, results_path: Path) -> dict:
    dataset = json.loads(dataset_path.read_text(encoding='utf-8'))
    cases = dataset.get('cases', [])

    passed = 0
    results = []
    for case in cases:
        text = case.get('output_json', '{}')
        ok = True
        reason = 'ok'
        try:
            StructuredExplanation.model_validate_json(text)
        except Exception as exc:  # noqa: BLE001
            ok = False
            reason = f'schema_invalid: {exc}'
        if ok:
            passed += 1
        results.append({'id': case.get('id'), 'pass': ok, 'reason': reason})

    summary = {
        'total': len(cases),
        'passed': passed,
        'failed': len(cases) - passed,
        'pass_rate': (passed / len(cases)) if cases else 0,
        'results': results,
    }
    write_stable_json(results_path, summary)
    return summary
