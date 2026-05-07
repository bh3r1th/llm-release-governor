from prompt_failure_analyzer.engine.analyzers import Finding
from prompt_failure_analyzer.engine.loader import prompt_to_lines


def _line_for_substring(lines: list[str], needle: str) -> int | None:
    needle_lower = needle.lower()
    for i, line in enumerate(lines, start=1):
        if needle_lower in line.lower():
            return i
    return None


def analyze_schema_risk(prompt: dict) -> list[Finding]:
    findings: list[Finding] = []
    lines = prompt_to_lines(prompt)
    text = "\n".join(lines).lower()

    if ("respond with" in text or "output" in text) and not any(
        token in text for token in ("json", "schema", "format", "structure", "object")
    ):
        findings.append(
            Finding(
                analyzer="schema_risk",
                severity="HIGH",
                pattern="UNTYPED_OUTPUT",
                message=(
                    "Prompt requests output without specifying format or schema. "
                    "High risk of schema drift in locc."
                ),
                line=_line_for_substring(lines, "respond with")
                or _line_for_substring(lines, "output"),
            )
        )

    if ("list of" in text or "array of" in text) and not any(
        token in text for token in ("each item", "format", "schema")
    ):
        findings.append(
            Finding(
                analyzer="schema_risk",
                severity="MEDIUM",
                pattern="IMPLICIT_LIST",
                message="Implicit list output with no item schema. Enum drift likely.",
                line=_line_for_substring(lines, "list of") or _line_for_substring(lines, "array of"),
            )
        )

    if any(token in text for token in ("if", "when", "unless", "otherwise")) and not any(
        token in text for token in ("return null", "return empty", "default", "fallback")
    ):
        findings.append(
            Finding(
                analyzer="schema_risk",
                severity="MEDIUM",
                pattern="NO_FALLBACK",
                message=(
                    "Conditional logic with no fallback output. "
                    "Missing fields risk under locc contract check."
                ),
                line=_line_for_substring(lines, "if")
                or _line_for_substring(lines, "when")
                or _line_for_substring(lines, "unless")
                or _line_for_substring(lines, "otherwise"),
            )
        )

    return findings

