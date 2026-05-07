"""Renders the release decision and leakage findings as a human-readable Markdown report."""

from release_governor.engine.decision import DecisionResult


def render_markdown(result: DecisionResult, artifact_hash: str, env: str) -> str:
    lines = [
        f"## Release Governor — {result.decision}",
        f"**Environment:** {env}",
        f"**Artifact Hash:** {artifact_hash}",
        "",
        "### Leakage Report",
        f"- PII: {result.leakage['pii']}",
        f"- Schema: {result.leakage['schema']}",
        f"- Policy: {result.leakage['policy']}",
        "",
        "### Notes",
    ]
    for note in result.notes:
        lines.append(f"- {note}")

    if result.override_failures:
        lines.append("")
        lines.append("### Override Failures")
        for failure in result.override_failures:
            lines.append(f"- {failure}")

    return "\n".join(lines)
