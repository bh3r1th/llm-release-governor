from prompt_failure_analyzer.engine.analyzers import Finding
from prompt_failure_analyzer.engine.loader import prompt_to_lines

PII_FIELDS = [
    "email",
    "phone",
    "ssn",
    "address",
    "date of birth",
    "social security",
    "credit card",
    "passport",
]


def _line_for_substring(lines: list[str], needle: str) -> int | None:
    needle_lower = needle.lower()
    for i, line in enumerate(lines, start=1):
        if needle_lower in line.lower():
            return i
    return None


def analyze_pii_risk(prompt: dict) -> list[Finding]:
    findings: list[Finding] = []
    lines = prompt_to_lines(prompt)
    text = "\n".join(lines).lower()

    for field in PII_FIELDS:
        line = _line_for_substring(lines, field)
        if line is not None:
            findings.append(
                Finding(
                    analyzer="pii_risk",
                    severity="HIGH",
                    pattern="PII_FIELD_REQUESTED",
                    message=(
                        f"Prompt explicitly requests PII field '{field}'. "
                        "Will trigger PII leakage detection in Release Governor."
                    ),
                    line=line,
                )
            )

    has_user_passthrough = any(
        token in text for token in ("user input", "user provided", "from the user")
    )
    has_guard = any(token in text for token in ("sanitize", "redact", "mask", "validate"))
    if has_user_passthrough and not has_guard:
        findings.append(
            Finding(
                analyzer="pii_risk",
                severity="MEDIUM",
                pattern="USER_DATA_PASSTHROUGH",
                message="Unguarded user data passthrough. PII may appear in LLM output.",
                line=_line_for_substring(lines, "user input")
                or _line_for_substring(lines, "user provided")
                or _line_for_substring(lines, "from the user"),
            )
        )

    if any(token in text for token in ("repeat", "echo", "return the user", "include the original")):
        findings.append(
            Finding(
                analyzer="pii_risk",
                severity="LOW",
                pattern="REFLECT_INPUT",
                message=(
                    "Input reflection pattern detected. Risk of PII propagation "
                    "if user input contains sensitive data."
                ),
                line=_line_for_substring(lines, "repeat")
                or _line_for_substring(lines, "echo")
                or _line_for_substring(lines, "return the user")
                or _line_for_substring(lines, "include the original"),
            )
        )

    return findings

