from pathlib import Path

import typer

from sheetproof.workbook.parser import parse_workbook, write_workbook_index

app = typer.Typer(help="Local-first spreadsheet audit and validation")


@app.command()
def audit(workbook: Path) -> None:
    """Audit a single workbook."""
    if not workbook.exists():
        raise typer.BadParameter(f"Workbook not found: {workbook}")
    index = parse_workbook(workbook)
    out_path = write_workbook_index(index, Path(".sheetproof"))
    typer.echo(f"Workbook index written: {out_path}")


@app.command()
def diff(old_workbook: Path, new_workbook: Path) -> None:
    """Compare two workbook versions."""
    typer.echo(f"[MVP scaffold] diff not implemented yet: {old_workbook} -> {new_workbook}")


@app.command()
def explain(workbook: Path, cell: str = typer.Option(..., "--cell")) -> None:
    """Explain logic for a specific cell."""
    typer.echo(f"[MVP scaffold] explain not implemented yet: {workbook} :: {cell}")


if __name__ == "__main__":
    app()
