from __future__ import annotations

DEFAULT_CONFIG = {
    "schema_version": 1,
    "local_only": False,
    "observability": {
        "trace_backend": "local",
        "primary_backend": "phoenix",
    },
    "llm": {
        "enabled": False,
        "provider": "local",
        "model": "qwen",
        "prompt_version": "v1",
        "timeout_seconds": 40,
        "max_retries": 2,
        "max_steps": 20,
        "constrained_output_engine": "pydantic",
    },
    "risk": {
        "high_risk_sheets": ["Summary", "Dashboard", "Inputs"],
        "severity_overrides": {
            "hidden_sheet_dependency": "high",
            "external_reference": "high",
            "hardcoded_override": "medium",
            "volatile_formula": "medium",
            "broken_reference": "high",
            "formula_inconsistency": "high",
        },
        "volatile_mode": "warn",
    },
    "policy_packs": {
        "finance": {
            "metadata": {
                "version": "1.0.0",
                "owner": "risk-finance",
                "rationale": "Conservative finance controls for model integrity.",
                "updated_at": "2026-05-18",
            },
            "risk": {
                "high_risk_sheets": ["Summary", "Dashboard", "Inputs"],
                "severity_overrides": {
                    "hidden_sheet_dependency": "high",
                    "external_reference": "high",
                    "hardcoded_override": "high",
                    "volatile_formula": "medium",
                    "broken_reference": "high",
                    "formula_inconsistency": "high",
                },
                "volatile_mode": "warn",
            }
        },
        "compliance": {
            "metadata": {
                "version": "1.0.0",
                "owner": "risk-compliance",
                "rationale": "Strict compliance posture with volatile-function denial.",
                "updated_at": "2026-05-18",
            },
            "risk": {
                "high_risk_sheets": ["Controls", "Risk", "Summary"],
                "severity_overrides": {
                    "hidden_sheet_dependency": "high",
                    "external_reference": "high",
                    "hardcoded_override": "medium",
                    "volatile_formula": "high",
                    "broken_reference": "high",
                    "formula_inconsistency": "high",
                },
                "volatile_mode": "deny",
            }
        },
        "operations": {
            "metadata": {
                "version": "1.0.0",
                "owner": "risk-operations",
                "rationale": "Operational monitoring posture with practical sensitivity.",
                "updated_at": "2026-05-18",
            },
            "risk": {
                "high_risk_sheets": ["Dashboard", "KPIs", "Inputs"],
                "severity_overrides": {
                    "hidden_sheet_dependency": "medium",
                    "external_reference": "high",
                    "hardcoded_override": "medium",
                    "volatile_formula": "low",
                    "broken_reference": "high",
                    "formula_inconsistency": "medium",
                },
                "volatile_mode": "warn",
            }
        },
    },
}
