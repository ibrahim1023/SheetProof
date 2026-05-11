import json
from pathlib import Path

from typer.testing import CliRunner

from sheetproof.cli import app


runner = CliRunner()


def test_eval_command_produces_results_and_nonzero_on_fail(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    ds = Path("dataset.json")
    ds.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "ok",
                        "output_json": json.dumps(
                            {
                                "summary": "Valid summary text",
                                "risks": [],
                                "reviewer_actions": [],
                                "citations": [],
                            }
                        ),
                    },
                    {"id": "bad", "output_json": "{}"},
                ]
            }
        ),
        encoding="utf-8",
    )
    out = Path("results.json")
    res = runner.invoke(app, ["eval-explain", "--dataset", str(ds), "--output", str(out)])
    assert res.exit_code == 21
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["failed"] == 1
