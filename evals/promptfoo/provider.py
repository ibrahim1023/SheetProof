from __future__ import annotations


def call_api(prompt: str, options: dict, context: dict) -> dict:
    vars_payload = context.get("vars", {})
    scenario = vars_payload.get("scenario", "faithful")
    cell = vars_payload.get("cell", "Summary!B3")
    if scenario == "refusal":
        return {"output": "Cannot explain this cell because deterministic artifacts are missing."}
    return {"output": f"Summary: Deterministic explanation for {cell}. Citations: {cell}"}
