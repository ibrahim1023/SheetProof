from pathlib import Path
import time
import uuid

import typer

from sheetproof.assumptions.detector import detect_assumptions
from sheetproof.benchmark import (
    compare_benchmark_to_baseline,
    run_audit_benchmark,
    write_benchmark_summary,
)
from sheetproof.config.loader import load_config
from sheetproof.diff.workbook_diff import compute_workbook_diff, render_diff_summary, write_workbook_diff
from sheetproof.formulas.extractor import extract_formula_inventory, write_formula_map
from sheetproof.graph.builder import build_dependency_graph
from sheetproof.graph.export import write_dependency_graph
from sheetproof.graph.impact import compute_downstream_impact
from sheetproof.gate import GateFailure, run_gate_flow
from sheetproof.integrations.export import export_ci_annotations, export_ticket_payload
from sheetproof.evals import run_explanation_eval, write_reliability_metrics
from sheetproof.llm.local_explainer import explain_cell
from sheetproof.observability import write_trace
from sheetproof.policy import effective_policy_context
from sheetproof.ragas_eval import run_ragas_eval
from sheetproof.reports.approval_trail import write_approval_trail
from sheetproof.reports.csv_export import write_assumption_register_csv, write_risk_cells_csv
from sheetproof.reports.json_report import write_json_report
from sheetproof.reports.markdown import write_markdown_report
from sheetproof.reports.reviewer_queue import write_reviewer_queue
from sheetproof.reports.repro_manifest import write_reproducibility_manifest
from sheetproof.workbook.attestation import write_coverage_matrix
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
    policy_context = effective_policy_context(cfg, policy_pack=policy_pack)
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
    json_report = write_json_report(
        index,
        formulas,
        findings,
        assumptions,
        out_dir,
        risk_policy,
        policy_context=policy_context,
    )
    write_coverage_matrix(out_dir)
    risk_csv = write_risk_cells_csv(findings, out_dir)
    assumptions_csv = write_assumption_register_csv(assumptions, out_dir)
    reviewer_queue = write_reviewer_queue(findings, out_dir)
    repro_manifest = write_reproducibility_manifest(out_dir)

    typer.echo(f"Workbook index written: {index_path}")
    typer.echo(f"Formula map written: {formula_map_path}")
    typer.echo(f"Dependency graph written: {graph_path}")
    typer.echo(f"Report written: {md_report}")
    typer.echo(f"Report written: {json_report}")
    typer.echo(f"Risk cells CSV written: {risk_csv}")
    typer.echo(f"Assumption register CSV written: {assumptions_csv}")
    typer.echo(f"Reviewer queue written: {reviewer_queue}")
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
    max_unattested_features: int = typer.Option(999999, "--max-unattested-features"),
    max_new_hidden_sheets: int = typer.Option(999999, "--max-new-hidden-sheets"),
    max_high_risk_changed_cells: int = typer.Option(999999, "--max-high-risk-changed-cells"),
    approved_by: str | None = typer.Option(None, "--approved-by"),
    approval_reason: str | None = typer.Option(None, "--approval-reason"),
    fail_on_warning: bool = typer.Option(False, "--fail-on-warning"),
) -> None:
    """Run deterministic approval gates for audit or diff mode."""
    start = time.perf_counter()
    request_id = str(uuid.uuid4())
    failures: list[GateFailure] = []
    out_dir = Path(".sheetproof")

    is_audit_mode = workbook is not None
    is_diff_mode = old_workbook is not None or new_workbook is not None
    if is_audit_mode and is_diff_mode:
        raise typer.BadParameter("Use either audit gate inputs or diff gate inputs, not both.")
    if not is_audit_mode and not is_diff_mode:
        raise typer.BadParameter("Provide --workbook or both --old-workbook and --new-workbook.")

    mode = "audit"
    cfg = load_config(policy_pack=policy_pack)
    policy_context = effective_policy_context(cfg, policy_pack=policy_pack)
    approval_trail_file: str | None = None
    if approved_by and approval_reason:
        approval_path = write_approval_trail(
            out_dir,
            request_id=request_id,
            mode=mode if is_audit_mode else "diff",
            approved_by=approved_by,
            approval_reason=approval_reason,
            policy_context=policy_context,
        )
        approval_trail_file = str(approval_path)
    write_trace(
        {
            "event": "gate_start",
            "request_id": request_id,
            "mode": mode if is_audit_mode else "diff",
            "provider": "deterministic",
            "model": "n/a",
            "prompt_version": "n/a",
        }
    )
    if is_audit_mode:
        if not workbook or not workbook.exists():
            raise typer.BadParameter(f"Workbook not found: {workbook}")
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
        if len(index.warning_codes) > max_unattested_features:
            failures.append(
                GateFailure(
                    rule="max_unattested_features",
                    actual=len(index.warning_codes),
                    threshold=max_unattested_features,
                    reason="Unsupported/unattested feature count exceeds threshold",
                    evidence=index.warning_codes[:10],
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
        write_coverage_matrix(out_dir)
        write_formula_map(formulas, out_dir)
        write_dependency_graph(graph, impact, out_dir)
        write_markdown_report(index, findings, assumptions, out_dir)
        write_json_report(
            index,
            formulas,
            findings,
            assumptions,
            out_dir,
            risk_policy,
            policy_context=policy_context,
        )
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

    result, out_path = run_gate_flow(
        mode=mode,
        failures=failures,
        out_dir=out_dir,
        policy_context=policy_context,
        approval_trail_file=approval_trail_file,
    )
    write_trace(
        {
            "event": "gate_complete" if result.passed else "gate_failed",
            "request_id": request_id,
            "mode": mode,
            "provider": "deterministic",
            "model": "n/a",
            "prompt_version": "n/a",
            "latency_ms": int((time.perf_counter() - start) * 1000),
            "error": None if result.passed else "; ".join(f.reason for f in result.failures),
        }
    )
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
    min_pass_rate: float = typer.Option(1.0, "--min-pass-rate"),
) -> None:
    """Run explanation schema evals."""
    if not dataset.exists():
        raise typer.BadParameter(f"Dataset not found: {dataset}")
    summary = run_explanation_eval(dataset, output)
    typer.echo(
        f"Eval complete: total={summary['total']} passed={summary['passed']} failed={summary['failed']} output={output}"
    )
    if summary["pass_rate"] < min_pass_rate:
        raise typer.Exit(code=21)


@app.command("benchmark-audit")
def benchmark_audit(
    workbook: Path = typer.Option(..., "--workbook"),
    runs: int = typer.Option(5, "--runs"),
    output: Path = typer.Option(Path("evals/results/audit_benchmark_latest.json"), "--output"),
    baseline: Path | None = typer.Option(
        None, "--baseline", help="Optional baseline JSON produced by benchmark-audit."
    ),
    max_regression_pct: float = typer.Option(
        25.0, "--max-regression-pct", help="Maximum allowed p95 runtime regression percentage."
    ),
) -> None:
    """Benchmark deterministic audit runtime and optionally gate against a baseline."""
    if not workbook.exists():
        raise typer.BadParameter(f"Workbook not found: {workbook}")
    summary = run_audit_benchmark(workbook=workbook, runs=runs)
    out = write_benchmark_summary(summary, output)
    typer.echo(f"Benchmark written: {out}")
    typer.echo(
        f"Runtime ms: min={summary.runtime_ms['min_ms']} avg={summary.runtime_ms['avg_ms']} "
        f"p95={summary.runtime_ms['p95_ms']} max={summary.runtime_ms['max_ms']}"
    )
    if baseline is not None:
        try:
            compare_benchmark_to_baseline(summary, baseline, max_regression_pct=max_regression_pct)
        except (ValueError, RuntimeError) as exc:
            typer.echo(f"Benchmark regression gate failed: {exc}")
            raise typer.Exit(code=22) from exc


@app.command("export-integrations")
def export_integrations(
    report: Path = typer.Option(Path(".sheetproof/sheetproof-report.json"), "--report"),
    out_dir: Path = typer.Option(Path(".sheetproof/integrations"), "--out-dir"),
) -> None:
    """Export deterministic machine-readable payloads for external review workflows."""
    if not report.exists():
        raise typer.BadParameter(f"Report not found: {report}")
    out_dir.mkdir(parents=True, exist_ok=True)
    ci_path = export_ci_annotations(report, out_dir / "ci-annotations.json")
    ticket_path = export_ticket_payload(report, out_dir / "ticket-export.json")
    typer.echo(f"Integration export written: {ci_path}")
    typer.echo(f"Integration export written: {ticket_path}")


@app.command("reliability-report")
def reliability_report(
    eval_results: Path = typer.Option(
        Path("evals/results/explain_eval_results.json"),
        "--eval-results",
    ),
    output: Path = typer.Option(
        Path("evals/results/reliability_metrics.json"),
        "--output",
    ),
    min_pass_rate: float = typer.Option(0.5, "--min-pass-rate"),
    min_refusal_rate: float = typer.Option(0.5, "--min-refusal-rate"),
) -> None:
    """Generate release-level reliability metrics and enforce thresholds."""
    if not eval_results.exists():
        raise typer.BadParameter(f"Eval results not found: {eval_results}")
    metrics = write_reliability_metrics(eval_results, output)
    typer.echo(
        f"Reliability metrics written: {output} pass_rate={metrics['pass_rate']:.3f} "
        f"refusal_correctness_rate={metrics['refusal_correctness_rate']:.3f}"
    )
    if metrics["pass_rate"] < min_pass_rate or metrics["refusal_correctness_rate"] < min_refusal_rate:
        raise typer.Exit(code=23)


@app.command("eval-ragas")
def eval_ragas(
    dataset: Path = typer.Option(Path("evals/datasets/explain_schema_cases.json"), "--dataset"),
    output: Path = typer.Option(Path("evals/results/ragas_metrics.json"), "--output"),
) -> None:
    """Run optional Ragas metrics for retrieval-style evaluation cases."""
    if not dataset.exists():
        raise typer.BadParameter(f"Dataset not found: {dataset}")
    payload = run_ragas_eval(dataset, output)
    typer.echo(
        f"Ragas eval written: {output} status={payload['status']} "
        f"applicable_cases={payload['applicable_cases']}"
    )


if __name__ == "__main__":
    app()
