import json
from pathlib import Path

from typer.testing import CliRunner

from sheetproof.cli import app


runner = CliRunner()


def test_reliability_report_outputs_metrics_and_threshold_gate(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    eval_results = Path("eval.json")
    eval_results.write_text(
        json.dumps(
            {
                "results": [
                    {"id": "faith_1", "pass": True, "reason": "ok"},
                    {"id": "refusal_1", "pass": True, "reason": "ok"},
                    {"id": "refusal_2", "pass": False, "reason": "refusal_expected_but_not_found"},
                ]
            }
        ),
        encoding="utf-8",
    )
    out = Path("reliability.json")
    res = runner.invoke(
        app,
        [
            "reliability-report",
            "--eval-results",
            str(eval_results),
            "--output",
            str(out),
            "--min-pass-rate",
            "0.5",
            "--min-refusal-rate",
            "0.4",
        ],
    )
    assert res.exit_code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["pass_rate"] > 0
    assert payload["refusal_correctness_rate"] > 0

    fail = runner.invoke(
        app,
        [
            "reliability-report",
            "--eval-results",
            str(eval_results),
            "--output",
            str(out),
            "--min-pass-rate",
            "0.9",
            "--min-refusal-rate",
            "0.9",
        ],
    )
    assert fail.exit_code == 23
