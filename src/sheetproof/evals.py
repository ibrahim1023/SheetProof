from __future__ import annotations

import json
from pathlib import Path

from sheetproof.llm.schemas import StructuredExplanation
from sheetproof.reproducibility import write_stable_json


def _is_refusal(text: str) -> bool:
    low = text.lower()
    return "cannot" in low or "can't" in low or "insufficient" in low or "missing" in low


def run_explanation_eval(dataset_path: Path, results_path: Path) -> dict:
    dataset = json.loads(dataset_path.read_text(encoding='utf-8'))
    cases = dataset.get('cases', [])

    passed = 0
    results = []
    for case in cases:
        text = case.get('output_json', '{}')
        ok = True
        reason = 'ok'
        parsed: StructuredExplanation | None = None
        try:
            parsed = StructuredExplanation.model_validate_json(text)
        except Exception as exc:  # noqa: BLE001
            ok = False
            reason = f'schema_invalid: {exc}'
        if ok and parsed is not None:
            case_type = case.get("type", "schema")
            if case_type == "faithfulness":
                required_cells = case.get("required_citations", [])
                cited = {c.cell for c in parsed.citations}
                missing = [c for c in required_cells if c not in cited]
                if missing:
                    ok = False
                    reason = f"faithfulness_missing_citations: {missing}"
            if case_type == "refusal":
                expect_refusal = bool(case.get("expect_refusal", True))
                refusal = _is_refusal(parsed.summary)
                if expect_refusal and not refusal:
                    ok = False
                    reason = "refusal_expected_but_not_found"
                if not expect_refusal and refusal:
                    ok = False
                    reason = "refusal_not_expected_but_found"
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
