from __future__ import annotations

from typing import Any

from sheetproof.reproducibility import canonicalize_for_hash, sha256_text


def effective_policy_context(config: dict[str, Any], policy_pack: str | None = None) -> dict[str, Any]:
    pack_name = policy_pack or "default"
    packs = config.get("policy_packs", {})
    pack_cfg = packs.get(pack_name, {}) if pack_name != "default" else {}
    metadata = pack_cfg.get("metadata", {})
    payload = {
        "pack": pack_name,
        "metadata": metadata,
        "risk": config.get("risk", {}),
    }
    canonical = canonicalize_for_hash(payload)
    import json

    digest = sha256_text(json.dumps(canonical, sort_keys=True, ensure_ascii=False))
    return {
        "pack": pack_name,
        "version": metadata.get("version", "1.0.0"),
        "owner": metadata.get("owner", "unknown"),
        "rationale": metadata.get("rationale", ""),
        "updated_at": metadata.get("updated_at", ""),
        "digest": digest,
        "signature": f"sha256:{digest}",
    }
