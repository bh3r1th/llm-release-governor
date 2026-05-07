import json

from prompt_failure_analyzer import __version__
from prompt_failure_analyzer.engine.analyzers import Finding
from prompt_failure_analyzer.engine.mapping import annotate_findings, summarize_locc_risk


def build_summary(findings: list[Finding]) -> dict:
    high = sum(1 for f in findings if f.severity == "HIGH")
    medium = sum(1 for f in findings if f.severity == "MEDIUM")
    low = sum(1 for f in findings if f.severity == "LOW")
    return {
        "total": len(findings),
        "high": high,
        "medium": medium,
        "low": low,
        "passed": high == 0,
    }


def render_json(findings: list[Finding], summary: dict, path: str) -> str:
    annotated_findings = annotate_findings(findings)
    locc_risk = summarize_locc_risk(findings)
    payload = {
        "version": __version__,
        "prompt_path": path,
        "summary": summary,
        "locc_risk": locc_risk,
        "findings": annotated_findings,
    }
    return json.dumps(payload, indent=2)


def render_markdown(findings: list[Finding], summary: dict, path: str) -> str:
    annotated_findings = annotate_findings(findings)
    locc_risk = summarize_locc_risk(findings)
    status = "PASSED" if summary["passed"] else "FAILED"
    emoji = "✅" if summary["passed"] else "🚫"

    lines = [
        f"## Prompt Failure Analyzer — {emoji} {status}",
        "",
        f"**Prompt:** {path}",
        (
            f"**Total findings:** {summary['total']} "
            f"({summary['high']} HIGH, {summary['medium']} MEDIUM, {summary['low']} LOW)"
        ),
        "",
    ]

    if findings:
        lines.append("### Findings")
        lines.append("")
        for finding in annotated_findings:
            lines.append(
                f"#### [{finding['severity']}] {finding['analyzer']} — {finding['pattern']}"
            )
            lines.append(finding["message"])
            lines.append(f"Line: {finding['line'] if finding['line'] is not None else 'N/A'}")
            if finding["predicted_locc_failures"]:
                codes = ", ".join(f"`{code}`" for code in finding["predicted_locc_failures"])
                lines.append(f"**Predicted locc failures:** {codes}")
            lines.append("")
        lines.append("### locc Risk Summary")
        predicted = ", ".join(f"`{c}`" for c in locc_risk["predicted_locc_failures"])
        high_risk = ", ".join(f"`{c}`" for c in locc_risk["high_risk_codes"])
        lines.append(f"**Predicted failures:** {predicted}")
        lines.append(f"**High-risk codes:** {high_risk}")
        lines.append("")

    lines.extend(
        [
            "### Summary",
            f"Passed: {summary['passed']}",
        ]
    )
    return "\n".join(lines)
