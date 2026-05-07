from pathlib import Path

import typer

from sheetproof.assumptions.detector import detect_assumptions
from sheetproof.diff.workbook_diff import compute_workbook_diff, render_diff_summary, write_workbook_diff
from sheetproof.formulas.extractor import extract_formula_inventory, write_formula_map
from sheetproof.graph.builder import build_dependency_graph
from sheetproof.graph.export import write_dependency_graph
from sheetproof.graph.impact import compute_downstream_impact
from sheetproof.llm.local_explainer import explain_cell
from sheetproof.reports.csv_export import write_assumption_register_csv, write_risk_cells_csv
from sheetproof.reports.json_report import write_json_report
from sheetproof.reports.markdown import write_markdown_report
from sheetproof.risk.rules import (
    dedupe_findings,
    detect_broken_reference_findings,
    detect_formula_inconsistency_findings,
    detect_hardcoded_override_findings,
    detect_hidden_external_dependency_findings,
    detect_volatile_formula_findings,
)
from sheetproof.risk.scorer import score_findings
from sheetproof.workbook.parser import parse_workbook, write_workbook_index

app = typer.Typer(help="Local-first spreadsheet audit and validation")


@app.command()
def audit(workbook: Path) -> None:
    """Audit a single workbook."""
    if not workbook.exists():
        raise typer.BadParameter(f"Workbook not found: {workbook}")
    out_dir = Path(".sheetproof")
    index = parse_workbook(workbook)
    index_path = write_workbook_index(index, out_dir)

    formulas = extract_formula_inventory(index)
    formula_map_path = write_formula_map(formulas, out_dir)

    graph = build_dependency_graph(formulas)
    impact = compute_downstream_impact(graph)
    graph_path = write_dependency_graph(graph, impact, out_dir)

    assumptions = detect_assumptions(index, impact)

    findings = []
    findings.extend(detect_formula_inconsistency_findings(formulas))
    findings.extend(detect_hardcoded_override_findings(index))
    findings.extend(detect_hidden_external_dependency_findings(index, formulas))
    findings.extend(detect_volatile_formula_findings(formulas))
    findings.extend(detect_broken_reference_findings(formulas))
    findings = dedupe_findings(findings)
    findings = score_findings(findings, impact)

    md_report = write_markdown_report(index, findings, assumptions, out_dir)
    json_report = write_json_report(index, formulas, findings, assumptions, out_dir)
    risk_csv = write_risk_cells_csv(findings, out_dir)
    assumptions_csv = write_assumption_register_csv(assumptions, out_dir)

    typer.echo(f"Workbook index written: {index_path}")
    typer.echo(f"Formula map written: {formula_map_path}")
    typer.echo(f"Dependency graph written: {graph_path}")
    typer.echo(f"Report written: {md_report}")
    typer.echo(f"Report written: {json_report}")
    typer.echo(f"Risk cells CSV written: {risk_csv}")
    typer.echo(f"Assumption register CSV written: {assumptions_csv}")


@app.command()
def diff(old_workbook: Path, new_workbook: Path) -> None:
    """Compare two workbook versions."""
    if not old_workbook.exists():
        raise typer.BadParameter(f"Old workbook not found: {old_workbook}")
    if not new_workbook.exists():
        raise typer.BadParameter(f"New workbook not found: {new_workbook}")

    result = compute_workbook_diff(old_workbook, new_workbook)
    out_path = write_workbook_diff(result, Path(".sheetproof"))
    typer.echo(render_diff_summary(result))
    typer.echo(f"Workbook diff written: {out_path}")


@app.command()
def explain(workbook: Path, cell: str = typer.Option(..., "--cell")) -> None:
    """Explain logic for a specific cell."""
    if not workbook.exists():
        raise typer.BadParameter(f"Workbook not found: {workbook}")
    try:
        explanation = explain_cell(workbook=workbook, cell=cell)
    except (ValueError, RuntimeError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(explanation)


if __name__ == "__main__":
    app()
