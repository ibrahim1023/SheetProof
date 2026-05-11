from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from sheetproof.config.loader import load_config
from sheetproof.llm.orchestrator import ExplainRunConfig, run_explain_flow
from sheetproof.llm.prompts import build_cell_explanation_prompt
from sheetproof.llm.providers import call_anthropic, call_gemini, call_openai
from sheetproof.llm.schemas import StructuredExplanation
from sheetproof.reproducibility import write_stable_json


@dataclass(frozen=True)
class DeterministicArtifacts:
    workbook_name: str
    formula_map: tuple[dict[str, Any], ...]
    dependency_graph: dict[str, Any]
    report_json: dict[str, Any]


@dataclass(frozen=True)
class DeterministicExplainContext:
    workbook: str
    cell: str
    formula: str | None
    findings: tuple[dict[str, Any], ...]
    dependencies: tuple[str, ...]

    def to_prompt_payload(self) -> dict[str, Any]:
        return {
            "workbook": self.workbook,
            "cell": self.cell,
            "formula": self.formula,
            "findings": list(self.findings),
            "dependencies": list(self.dependencies),
        }


def load_deterministic_artifacts(workbook: Path, artifacts_dir: Path = Path(".sheetproof")) -> DeterministicArtifacts:
    report_path = artifacts_dir / "sheetproof-report.json"
    formula_map_path = artifacts_dir / "formula-map.json"
    graph_path = artifacts_dir / "dependency-graph.json"

    missing = [str(p) for p in [report_path, formula_map_path, graph_path] if not p.exists()]
    if missing:
        raise ValueError(
            "Missing deterministic artifacts required for explain: "
            + ", ".join(missing)
            + ". Run `sheetproof audit <workbook.xlsx>` first."
        )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    formula_map = json.loads(formula_map_path.read_text(encoding="utf-8"))
    graph = json.loads(graph_path.read_text(encoding="utf-8"))

    report_workbook = report.get("workbook", {}).get("name")
    if report_workbook and report_workbook != workbook.name:
        raise ValueError(
            f"Deterministic artifacts belong to workbook `{report_workbook}`, not `{workbook.name}`. "
            "Re-run audit for the requested workbook."
        )

    findings = report.get("findings", [])
    for f in findings:
        if f.get("source") != "deterministic":
            raise ValueError(
                "Explain is blocked: findings provenance is not deterministic. "
                "Re-run audit to regenerate trusted artifacts."
            )

    return DeterministicArtifacts(
        workbook_name=report_workbook or workbook.name,
        formula_map=tuple(formula_map),
        dependency_graph=graph,
        report_json=report,
    )


def _cell_context(cell: str, artifacts: DeterministicArtifacts) -> DeterministicExplainContext:
    sheet, _, cell_ref = cell.partition("!")
    if not sheet or not cell_ref:
        raise ValueError("Cell must be in `Sheet!A1` format.")

    formula_item = next(
        (x for x in artifacts.formula_map if x.get("sheet") == sheet and x.get("cell") == cell_ref),
        None,
    )

    findings = tuple(
        f
        for f in artifacts.report_json.get("findings", [])
        if f.get("sheet") == sheet and f.get("cell") == cell_ref
    )

    node_name = f"{sheet}!{cell_ref}"
    deps = tuple(
        e.get("source")
        for e in artifacts.dependency_graph.get("edges", [])
        if e.get("target") == node_name
    )

    return DeterministicExplainContext(
        workbook=artifacts.workbook_name,
        cell=cell,
        formula=formula_item.get("formula") if formula_item else None,
        findings=findings,
        dependencies=deps,
    )


def explain_with_ollama(prompt: str, model: str, base_url: str = "http://localhost:11434") -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }

    req = Request(
        url=f"{base_url.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except URLError as exc:
        raise RuntimeError(
            "Failed to reach Ollama at http://localhost:11434. "
            "Ensure Ollama is running locally."
        ) from exc

    message = body.get("message", {})
    content = message.get("content")
    if not content:
        raise RuntimeError("Ollama returned an empty explanation response.")
    return str(content).strip()


def write_explanation_artifact(
    workbook: Path,
    cell: str,
    explanation: StructuredExplanation,
    out_dir: Path = Path(".sheetproof"),
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "explanations.json"

    payload: dict[str, Any]
    if out_file.exists():
        payload = json.loads(out_file.read_text(encoding="utf-8"))
    else:
        payload = {"explanations": []}

    payload.setdefault("explanations", []).append(
        {
            "workbook": workbook.name,
            "cell": cell,
            "source": "llm_explanation",
            "explanation": explanation.model_dump(),
        }
    )
    write_stable_json(out_file, payload)
    return out_file


def explain_cell(workbook: Path, cell: str) -> str:
    cfg = load_config()
    llm_cfg = cfg.get("llm", {})
    if llm_cfg.get("enabled") is False:
        raise ValueError("LLM explanations are disabled in config (`llm.enabled: false`).")

    provider = llm_cfg.get("provider", "local")
    if provider not in {"local", "ollama", "openai", "anthropic", "gemini"}:
        raise ValueError(
            "Unsupported provider. Expected one of: local, ollama, openai, anthropic, gemini."
        )

    model = llm_cfg.get("model", "qwen")
    base_url = llm_cfg.get("base_url", "http://localhost:11434")

    artifacts = load_deterministic_artifacts(workbook)
    context = _cell_context(cell, artifacts)

    def _provider_call(prompt: str) -> str:
        if provider in {"local", "ollama"}:
            return explain_with_ollama(prompt=prompt, model=model, base_url=base_url)
        if provider == "openai":
            return call_openai(
                prompt=prompt,
                model=model,
                base_url=llm_cfg.get("openai_base_url"),
                api_key=llm_cfg.get("openai_api_key"),
            )
        if provider == "anthropic":
            return call_anthropic(
                prompt=prompt,
                model=model,
                api_key=llm_cfg.get("anthropic_api_key"),
            )
        if provider == "gemini":
            return call_gemini(
                prompt=prompt,
                model=model,
                api_key=llm_cfg.get("gemini_api_key"),
            )
        raise RuntimeError(f"Unsupported provider: {provider}")

    explanation = run_explain_flow(
        ExplainRunConfig(workbook_name=workbook.name, cell=cell, model=model),
        build_prompt=lambda: build_cell_explanation_prompt(cell, context.to_prompt_payload()),
        provider_call=_provider_call,
    )
    write_explanation_artifact(workbook, cell, explanation)
    lines = [f"Summary: {explanation.summary}"]
    if explanation.risks:
        lines.append("Risks:")
        lines.extend([f"- {r}" for r in explanation.risks])
    if explanation.reviewer_actions:
        lines.append("Reviewer Actions:")
        lines.extend([f"- {a}" for a in explanation.reviewer_actions])
    if explanation.citations:
        lines.append("Citations:")
        lines.extend([f"- {c.cell}: {c.reason}" for c in explanation.citations])
    return "\n".join(lines)
