from pathlib import Path

import typer

from sheetproof.assumptions.detector import detect_assumptions
from sheetproof.config.loader import load_config
from sheetproof.diff.workbook_diff import compute_workbook_diff, render_diff_summary, write_workbook_diff
from sheetproof.formulas.extractor import extract_formula_inventory, write_formula_map
from sheetproof.graph.builder import build_dependency_graph
from sheetproof.graph.export import write_dependency_graph
from sheetproof.graph.impact import compute_downstream_impact
from sheetproof.gate import GateFailure, build_gate_result, write_gate_result
from sheetproof.evals import run_explanation_eval
from sheetproof.llm.local_explainer import explain_cell
from sheetproof.reports.csv_export import write_assumption_register_csv, write_risk_cells_csv
from sheetproof.reports.json_report import write_json_report
from sheetproof.reports.markdown import write_markdown_report
from sheetproof.reports.repro_manifest import write_reproducibility_manifest
from sheetproof.risk.rules import (
    dedupe_findings,
    detect_broken_reference_findings,
    detect_formula_inconsistency_findings,
    detect_hardcoded_override_findings,
    detect_hidden_external_dependency_findings,
    detect_volatile_formula_findings,
)
from sheetproof.risk.scorer import score_findings
from sheetproof.risk.lineage import enrich_findings_with_lineage
from sheetproof.workbook.parser import parse_workbook, write_workbook_index

app = typer.Typer(help="Local-first spreadsheet audit and validation")


@app.command()
def audit(
    workbook: Path,
    deterministic: bool = typer.Option(
        False,
        "--deterministic",
        help="Emit deterministic artifacts (suppresses volatile metadata fields).",
    ),
    policy_pack: str | None = typer.Option(
        None,
        "--policy-pack",
        help="Apply a deterministic policy pack (finance, compliance, operations).",
    ),
) -> None:
    """Audit a single workbook."""
    if not workbook.exists():
        raise typer.BadParameter(f"Workbook not found: {workbook}")
    try:
        cfg = load_config(policy_pack=policy_pack)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    risk_policy = cfg.get("risk", {})
    out_dir = Path(".sheetproof")
    index = parse_workbook(workbook, deterministic=deterministic)
    index_path = write_workbook_index(index, out_dir)

    formulas = extract_formula_inventory(index)
    formula_map_path = write_formula_map(formulas, out_dir)

    graph = build_dependency_graph(formulas)
    impact = compute_downstream_impact(graph)
    graph_path = write_dependency_graph(graph, impact, out_dir)

    assumptions = detect_assumptions(index, impact, graph)

    findings = []
    findings.extend(detect_formula_inconsistency_findings(formulas, risk_policy))
    findings.extend(detect_hardcoded_override_findings(index, risk_policy))
    findings.extend(detect_hidden_external_dependency_findings(index, formulas, risk_policy))
    findings.extend(detect_volatile_formula_findings(formulas, risk_policy))
    findings.extend(detect_broken_reference_findings(formulas, risk_policy))
    findings = dedupe_findings(findings)
    findings = score_findings(findings, impact)
    findings = enrich_findings_with_lineage(findings, graph, impact)

    md_report = write_markdown_report(index, findings, assumptions, out_dir)
    json_report = write_json_report(index, formulas, findings, assumptions, out_dir, risk_policy)
    risk_csv = write_risk_cells_csv(findings, out_dir)
    assumptions_csv = write_assumption_register_csv(assumptions, out_dir)
    repro_manifest = write_reproducibility_manifest(out_dir)

    typer.echo(f"Workbook index written: {index_path}")
    typer.echo(f"Formula map written: {formula_map_path}")
    typer.echo(f"Dependency graph written: {graph_path}")
    typer.echo(f"Report written: {md_report}")
    typer.echo(f"Report written: {json_report}")
    typer.echo(f"Risk cells CSV written: {risk_csv}")
    typer.echo(f"Assumption register CSV written: {assumptions_csv}")
    typer.echo(f"Reproducibility manifest written: {repro_manifest}")


@app.command()
def diff(
    old_workbook: Path,
    new_workbook: Path,
    policy_pack: str | None = typer.Option(
        None,
        "--policy-pack",
        help="Apply a deterministic policy pack (finance, compliance, operations).",
    ),
) -> None:
    """Compare two workbook versions."""
    if not old_workbook.exists():
        raise typer.BadParameter(f"Old workbook not found: {old_workbook}")
    if not new_workbook.exists():
        raise typer.BadParameter(f"New workbook not found: {new_workbook}")

    result = compute_workbook_diff(old_workbook, new_workbook, policy_pack=policy_pack)
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


@app.command()
def gate(
    workbook: Path | None = typer.Option(
        None, "--workbook", help="Workbook path for audit gate mode."
    ),
    old_workbook: Path | None = typer.Option(
        None, "--old-workbook", help="Old workbook path for diff gate mode."
    ),
    new_workbook: Path | None = typer.Option(
        None, "--new-workbook", help="New workbook path for diff gate mode."
    ),
    policy_pack: str | None = typer.Option(
        None,
        "--policy-pack",
        help="Apply a deterministic policy pack (finance, compliance, operations).",
    ),
    max_high_risk_findings: int = typer.Option(999999, "--max-high-risk-findings"),
    max_external_references: int = typer.Option(999999, "--max-external-references"),
    max_new_hidden_sheets: int = typer.Option(999999, "--max-new-hidden-sheets"),
    max_high_risk_changed_cells: int = typer.Option(999999, "--max-high-risk-changed-cells"),
    fail_on_warning: bool = typer.Option(False, "--fail-on-warning"),
) -> None:
    """Run deterministic approval gates for audit or diff mode."""
    failures: list[GateFailure] = []
    out_dir = Path(".sheetproof")

    is_audit_mode = workbook is not None
    is_diff_mode = old_workbook is not None or new_workbook is not None
    if is_audit_mode and is_diff_mode:
        raise typer.BadParameter("Use either audit gate inputs or diff gate inputs, not both.")
    if not is_audit_mode and not is_diff_mode:
        raise typer.BadParameter("Provide --workbook or both --old-workbook and --new-workbook.")

    mode = "audit"
    if is_audit_mode:
        if not workbook or not workbook.exists():
            raise typer.BadParameter(f"Workbook not found: {workbook}")
        cfg = load_config(policy_pack=policy_pack)
        risk_policy = cfg.get("risk", {})

        index = parse_workbook(workbook, deterministic=True)
        formulas = extract_formula_inventory(index)
        graph = build_dependency_graph(formulas)
        impact = compute_downstream_impact(graph)
        assumptions = detect_assumptions(index, impact, graph)

        findings = []
        findings.extend(detect_formula_inconsistency_findings(formulas, risk_policy))
        findings.extend(detect_hardcoded_override_findings(index, risk_policy))
        findings.extend(detect_hidden_external_dependency_findings(index, formulas, risk_policy))
        findings.extend(detect_volatile_formula_findings(formulas, risk_policy))
        findings.extend(detect_broken_reference_findings(formulas, risk_policy))
        findings = dedupe_findings(findings)
        findings = score_findings(findings, impact)
        findings = enrich_findings_with_lineage(findings, graph, impact)

        high_risk_findings = [f for f in findings if f.severity == "high"]
        external_refs = [f for f in findings if f.type == "external_reference"]
        warning_findings = [f for f in findings if f.severity in {"low", "medium"}]

        if len(high_risk_findings) > max_high_risk_findings:
            failures.append(
                GateFailure(
                    rule="max_high_risk_findings",
                    actual=len(high_risk_findings),
                    threshold=max_high_risk_findings,
                    reason="High-risk finding count exceeds threshold",
                    evidence=[f"{f.sheet}!{f.cell}" for f in high_risk_findings[:10]],
                )
            )
        if len(external_refs) > max_external_references:
            failures.append(
                GateFailure(
                    rule="max_external_references",
                    actual=len(external_refs),
                    threshold=max_external_references,
                    reason="External reference count exceeds threshold",
                    evidence=[f"{f.sheet}!{f.cell}" for f in external_refs[:10]],
                )
            )
        if fail_on_warning and warning_findings:
            failures.append(
                GateFailure(
                    rule="fail_on_warning",
                    actual=len(warning_findings),
                    threshold=0,
                    reason="Warnings are not allowed",
                    evidence=[f"{f.sheet}!{f.cell}" for f in warning_findings[:10]],
                )
            )

        # keep audit artifacts available for review even in gate mode
        write_workbook_index(index, out_dir)
        write_formula_map(formulas, out_dir)
        write_dependency_graph(graph, impact, out_dir)
        write_markdown_report(index, findings, assumptions, out_dir)
        write_json_report(index, formulas, findings, assumptions, out_dir, risk_policy)
        write_risk_cells_csv(findings, out_dir)
        write_assumption_register_csv(assumptions, out_dir)
        write_reproducibility_manifest(out_dir)
    else:
        mode = "diff"
        if not old_workbook or not old_workbook.exists():
            raise typer.BadParameter(f"Old workbook not found: {old_workbook}")
        if not new_workbook or not new_workbook.exists():
            raise typer.BadParameter(f"New workbook not found: {new_workbook}")

        diff_result = compute_workbook_diff(
            old_workbook,
            new_workbook,
            policy_pack=policy_pack,
        )
        write_workbook_diff(diff_result, out_dir)

        if diff_result.newly_hidden_sheets and len(diff_result.newly_hidden_sheets) > max_new_hidden_sheets:
            failures.append(
                GateFailure(
                    rule="max_new_hidden_sheets",
                    actual=len(diff_result.newly_hidden_sheets),
                    threshold=max_new_hidden_sheets,
                    reason="New hidden sheet count exceeds threshold",
                    evidence=diff_result.newly_hidden_sheets[:10],
                )
            )

        if diff_result.high_risk_changed_cells > max_high_risk_changed_cells:
            high_cells = [f"{c.sheet}!{c.cell}" for c in diff_result.changes if c.high_risk][:10]
            failures.append(
                GateFailure(
                    rule="max_high_risk_changed_cells",
                    actual=diff_result.high_risk_changed_cells,
                    threshold=max_high_risk_changed_cells,
                    reason="High-risk changed cell count exceeds threshold",
                    evidence=high_cells,
                )
            )

        if diff_result.new_external_references and len(diff_result.new_external_references) > max_external_references:
            failures.append(
                GateFailure(
                    rule="max_external_references",
                    actual=len(diff_result.new_external_references),
                    threshold=max_external_references,
                    reason="New external reference count exceeds threshold",
                    evidence=diff_result.new_external_references[:10],
                )
            )

    result = build_gate_result(mode=mode, failures=failures)
    out_path = write_gate_result(result, out_dir)
    typer.echo(f"Gate result written: {out_path}")
    typer.echo(f"Gate passed: {result.passed}")
    if not result.passed:
        for f in result.failures:
            typer.echo(f"- {f.rule}: actual={f.actual} threshold={f.threshold} ({f.reason})")
        raise typer.Exit(code=result.exit_code)


@app.command("eval-explain")
def eval_explain(
    dataset: Path = typer.Option(Path("evals/datasets/explain_schema_cases.json"), "--dataset"),
    output: Path = typer.Option(Path("evals/results/explain_eval_results.json"), "--output"),
) -> None:
    """Run explanation schema evals."""
    if not dataset.exists():
        raise typer.BadParameter(f"Dataset not found: {dataset}")
    summary = run_explanation_eval(dataset, output)
    typer.echo(
        f"Eval complete: total={summary['total']} passed={summary['passed']} failed={summary['failed']} output={output}"
    )
    if summary["failed"] > 0:
        raise typer.Exit(code=21)


if __name__ == "__main__":
    app()
