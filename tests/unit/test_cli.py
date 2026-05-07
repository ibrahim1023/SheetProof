from typer.testing import CliRunner

from sheetproof.cli import app


runner = CliRunner()


def test_help_renders() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "spreadsheet audit" in result.stdout.lower()
