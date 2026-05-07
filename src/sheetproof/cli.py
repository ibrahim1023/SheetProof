from pathlib import Path

import typer

app = typer.Typer(help="Local-first spreadsheet audit and validation")


@app.command()
def audit(workbook: Path) -> None:
    """Audit a single workbook."""
    typer.echo(f"[MVP scaffold] audit not implemented yet: {workbook}")


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
