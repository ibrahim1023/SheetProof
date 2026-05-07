from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from sheetproof.config.loader import load_config
from sheetproof.llm.prompts import build_cell_explanation_prompt


@dataclass
class DeterministicArtifacts:
    workbook_name: str
    formula_map: list[dict[str, Any]]
    dependency_graph: dict[str, Any]
    report_json: dict[str, Any]


def load_deterministic_artifacts(workbook: Path, artifacts_dir: Path = Path(".sheetproof")) -> DeterministicArtifacts:
    report_path = artifacts_dir / "sheetproof-report.json"
    formula_map_path = artifacts_dir / "formula-map.json"
    graph_path = artifacts_dir / "dependency-graph.json"

    missing = [
        str(p)
        for p in [report_path, formula_map_path, graph_path]
        if not p.exists()
    ]
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

    return DeterministicArtifacts(
        workbook_name=report_workbook or workbook.name,
        formula_map=formula_map,
        dependency_graph=graph,
        report_json=report,
    )


def _cell_context(cell: str, artifacts: DeterministicArtifacts) -> dict[str, Any]:
    sheet, _, cell_ref = cell.partition("!")
    if not sheet or not cell_ref:
        raise ValueError("Cell must be in `Sheet!A1` format.")

    formula_item = next(
        (
            x
            for x in artifacts.formula_map
            if x.get("sheet") == sheet and x.get("cell") == cell_ref
        ),
        None,
    )

    findings = [
        f
        for f in artifacts.report_json.get("findings", [])
        if f.get("sheet") == sheet and f.get("cell") == cell_ref
    ]

    node_name = f"{sheet}!{cell_ref}"
    deps = [
        e.get("source")
        for e in artifacts.dependency_graph.get("edges", [])
        if e.get("target") == node_name
    ]

    return {
        "workbook": artifacts.workbook_name,
        "cell": cell,
        "formula": formula_item.get("formula") if formula_item else None,
        "findings": findings,
        "dependencies": deps,
    }


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


def explain_cell(workbook: Path, cell: str) -> str:
    cfg = load_config()
    llm_cfg = cfg.get("llm", {})
    if llm_cfg.get("enabled") is False:
        raise ValueError("LLM explanations are disabled in config (`llm.enabled: false`).")

    provider = llm_cfg.get("provider", "local")
    if provider not in {"local", "ollama"}:
        raise ValueError(f"Phase 3.1 supports only local Ollama provider. Got: {provider}")

    model = llm_cfg.get("model", "qwen")
    base_url = llm_cfg.get("base_url", "http://localhost:11434")

    artifacts = load_deterministic_artifacts(workbook)
    context = _cell_context(cell, artifacts)
    prompt = build_cell_explanation_prompt(cell, context)
    return explain_with_ollama(prompt=prompt, model=model, base_url=base_url)
