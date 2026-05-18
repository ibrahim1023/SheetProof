import json
from pathlib import Path

from sheetproof.ragas_eval import run_ragas_eval


def test_ragas_eval_not_applicable_when_no_retrieval_cases(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.json"
    dataset.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "schema_only_1",
                        "type": "schema",
                        "output_json": "{}",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "ragas.json"
    payload = run_ragas_eval(dataset, out)
    assert payload["status"] == "not_applicable"
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["status"] == "not_applicable"


def test_ragas_eval_marks_unavailable_without_runtime(tmp_path: Path, monkeypatch) -> None:
    dataset = tmp_path / "cases.json"
    dataset.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "ragas_1",
                        "question": "What changed?",
                        "answer": "Revenue input changed.",
                        "contexts": ["Cell Inputs!B2 changed from 100 to 120."],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):  # type: ignore[no-untyped-def]
        if name in {"ragas", "datasets"}:
            raise ImportError("missing optional dependency")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    out = tmp_path / "ragas.json"
    payload = run_ragas_eval(dataset, out)
    assert payload["status"] == "unavailable"
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["status"] == "unavailable"
