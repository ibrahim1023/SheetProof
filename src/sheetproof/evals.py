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


def write_reliability_metrics(eval_results_path: Path, output_path: Path) -> dict:
    payload = json.loads(eval_results_path.read_text(encoding="utf-8"))
    results = payload.get("results", [])
    total = len(results)
    passed = sum(1 for r in results if r.get("pass") is True)
    failed = total - passed

    refusal_total = 0
    refusal_passed = 0
    failure_taxonomy: dict[str, int] = {}
    for r in results:
        reason = str(r.get("reason", "unknown"))
        if "refusal" in str(r.get("id", "")).lower():
            refusal_total += 1
            if r.get("pass") is True:
                refusal_passed += 1
        key = reason.split(":", 1)[0]
        failure_taxonomy[key] = failure_taxonomy.get(key, 0) + (0 if r.get("pass") else 1)

    metrics = {
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": failed,
        "pass_rate": (passed / total) if total else 0.0,
        "refusal_total": refusal_total,
        "refusal_passed": refusal_passed,
        "refusal_correctness_rate": (refusal_passed / refusal_total) if refusal_total else 1.0,
        "failure_taxonomy": dict(sorted(failure_taxonomy.items())),
    }
    write_stable_json(output_path, metrics)
    return metrics
