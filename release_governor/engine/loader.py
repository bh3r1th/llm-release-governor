"""Loads and validates locc artifacts (LLM change manifests) from CI for downstream engine processing."""

import hashlib
import json


def load_locc_artifact(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            artifact = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e

    missing = [k for k in ("version", "status", "checks") if k not in artifact]
    if missing:
        raise ValueError(f"Artifact missing required keys: {missing}")

    return artifact


def compute_identity_hash(artifact: dict) -> str:
    return hashlib.sha256(
        json.dumps(artifact, sort_keys=True).encode()
    ).hexdigest()


def load_override_file(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            override = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e

    required = {
        "approved_by", "reason", "scope", "expires_at",
        "approved_head_sha", "leakage_types", "identity_hash",
    }
    missing = [k for k in required if k not in override]
    if missing:
        raise ValueError(f"Override missing required keys: {missing}")

    return override
