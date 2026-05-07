import re

from prompt_failure_analyzer.engine.analyzers import Finding
from prompt_failure_analyzer.engine.loader import prompt_to_lines


def _line_for_substring(lines: list[str], needle: str) -> int | None:
    needle_lower = needle.lower()
    for i, line in enumerate(lines, start=1):
        if needle_lower in line.lower():
            return i
    return None


def analyze_constraint_risk(prompt: dict) -> list[Finding]:
    findings: list[Finding] = []
    lines = prompt_to_lines(prompt)
    text = "\n".join(lines).lower()

    has_hard = any(token in text for token in ("always", "never", "must", "required"))
    has_hedge = any(token in text for token in ("if possible", "when available", "try to", "as much as possible"))
    if has_hard and has_hedge:
        findings.append(
            Finding(
                analyzer="constraint_risk",
                severity="HIGH",
                pattern="AMBIGUOUS_CONSTRAINT",
                message=(
                    "Hard constraint softened by hedging language. "
                    "EGA will treat this as a hard rule; model may not."
                ),
                line=_line_for_substring(lines, "always")
                or _line_for_substring(lines, "never")
                or _line_for_substring(lines, "must")
                or _line_for_substring(lines, "required"),
            )
        )

    has_short = any(token in text for token in ("short", "brief", "concise"))
    has_detailed = any(
        token in text for token in ("detailed", "comprehensive", "thorough", "exhaustive")
    )
    if has_short and has_detailed:
        findings.append(
            Finding(
                analyzer="constraint_risk",
                severity="HIGH",
                pattern="CONFLICTING_INSTRUCTIONS",
                message=(
                    "Conflicting length instructions. Undefined model behavior; "
                    "high EGA violation risk."
                ),
                line=_line_for_substring(lines, "short")
                or _line_for_substring(lines, "brief")
                or _line_for_substring(lines, "concise"),
            )
        )

    for term in ("appropriate", "reasonable", "relevant", "good", "best"):
        pattern = re.compile(rf"\b{term}\b")
        for match in pattern.finditer(text):
            follow = text[match.end() : match.end() + 50]
            if any(token in follow for token in ("for example", "e.g.", "defined as", ":")):
                continue
            line = text[: match.start()].count("\n") + 1
            findings.append(
                Finding(
                    analyzer="constraint_risk",
                    severity="MEDIUM",
                    pattern="UNDEFINED_TERM",
                    message=(
                        f"Undefined subjective term '{term}'. Model interpretation "
                        "will vary; contract violations likely."
                    ),
                    line=line,
                )
            )

    return findings

