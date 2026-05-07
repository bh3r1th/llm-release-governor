"""Renders the release decision as a GitHub PR comment and posts it via the REST API."""

import json
from pathlib import Path

import requests

from release_governor.engine.decision import DecisionResult

_DECISION_EMOJI = {
    "ALLOW": "✅",
    "BLOCK": "🚫",
    "REQUIRE_OVERRIDE": "⚠️",
}


def _leakage_icon(detected: bool) -> str:
    return "🚫" if detected else "✅"


def render_pr_comment(
    result: DecisionResult,
    artifact_hash: str,
    env: str,
    artifact_path: str,
    pfa_summary: dict | None = None,
) -> str:
    emoji = _DECISION_EMOJI[result.decision]
    lines = [
        f"## Release Governor — {emoji} {result.decision}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Environment | {env} |",
        f"| Artifact Hash | `{artifact_hash}` |",
        f"| Decision | {result.decision} |",
        "",
        "### Leakage Detected",
        f"- PII: {_leakage_icon(result.leakage['pii'])}",
        f"- Schema: {_leakage_icon(result.leakage['schema'])}",
        f"- Policy: {_leakage_icon(result.leakage['policy'])}",
        "",
        "### Notes",
    ]

    if pfa_summary is not None:
        lines.extend(
            [
                "",
                "### PFA Pre-flight",
                (
                    f"**Findings:** {pfa_summary['total']} ({pfa_summary['high']} HIGH, "
                    f"{pfa_summary['medium']} MEDIUM, {pfa_summary['low']} LOW)"
                ),
            ]
        )
        predicted = pfa_summary.get("locc_risk", {}).get("predicted_locc_failures", [])
        if predicted:
            rendered_codes = ", ".join(f"`{code}`" for code in predicted)
            lines.append(f"**Predicted locc failures:** {rendered_codes}")
        lines.append(f"**Status:** {'✅ Passed' if pfa_summary['passed'] else '🚫 Failed'}")

    for note in result.notes:
        lines.append(f"- {note}")

    if result.override_failures:
        lines.append("")
        lines.append("### Override Failures")
        for failure in result.override_failures:
            lines.append(f"- {failure}")
        lines.append("")
        lines.append(f"> To resolve: commit a valid override file to `overrides/{env}/active.json`")

    lines.append("")
    lines.append("### Artifact")
    lines.append(f"`{artifact_path}`")

    return "\n".join(lines)


def post_pr_comment(body: str, repo: str, pr_number: int, token: str) -> None:
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    response = requests.post(
        url,
        json={"body": body},
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=30,
    )
    if response.status_code != 201:
        raise RuntimeError(
            f"Failed to post PR comment: HTTP {response.status_code} — {response.text}"
        )


def load_pfa_summary(pfa_findings_path: str | None) -> dict | None:
    if not pfa_findings_path:
        return None

    path = Path(pfa_findings_path)
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        summary = payload.get("summary", {})
        return {
            "total": summary.get("total"),
            "high": summary.get("high"),
            "medium": summary.get("medium"),
            "low": summary.get("low"),
            "passed": summary.get("passed"),
            "locc_risk": payload.get("locc_risk", {}),
        }
    except Exception:
        return None
