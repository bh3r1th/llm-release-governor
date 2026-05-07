"""Serializes the release decision and leakage findings to a structured JSON report."""

import json

from release_governor.engine.decision import DecisionResult


def render_json(result: DecisionResult, artifact_hash: str, env: str) -> str:
    return json.dumps(
        {
            "decision": result.decision,
            "env": env,
            "artifact_hash": artifact_hash,
            "leakage": result.leakage,
            "override_failures": result.override_failures,
            "notes": result.notes,
        },
        indent=2,
    )
