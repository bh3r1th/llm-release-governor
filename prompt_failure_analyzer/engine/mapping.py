from dataclasses import asdict

from prompt_failure_analyzer.engine.analyzers import Finding

PFA_TO_LOCC: dict[str, list[str]] = {
    "UNTYPED_OUTPUT": ["schema.type_mismatch", "schema.missing_field"],
    "IMPLICIT_LIST": ["schema.enum_drift", "schema.type_mismatch"],
    "NO_FALLBACK": ["schema.missing_field", "contract.hold_threshold"],
    "PII_FIELD_REQUESTED": ["pii.direct_exposure", "contract.pii_policy"],
    "USER_DATA_PASSTHROUGH": ["pii.indirect_exposure", "contract.pii_policy"],
    "REFLECT_INPUT": ["pii.indirect_exposure"],
    "AMBIGUOUS_CONSTRAINT": ["contract.hard_constraint_violated"],
    "CONFLICTING_INSTRUCTIONS": [
        "contract.hard_constraint_violated",
        "contract.hold_threshold",
    ],
    "UNDEFINED_TERM": ["contract.hold_threshold"],
}


def get_locc_codes(pattern: str) -> list[str]:
    return PFA_TO_LOCC.get(pattern, [])


def annotate_findings(findings: list[Finding]) -> list[dict]:
    annotated: list[dict] = []
    for finding in findings:
        item = asdict(finding)
        item["predicted_locc_failures"] = get_locc_codes(finding.pattern)
        annotated.append(item)
    return annotated


def summarize_locc_risk(findings: list[Finding]) -> dict:
    all_codes: set[str] = set()
    high_codes: set[str] = set()
    count_by_code: dict[str, int] = {}

    for finding in findings:
        codes = get_locc_codes(finding.pattern)
        for code in codes:
            all_codes.add(code)
            count_by_code[code] = count_by_code.get(code, 0) + 1
            if finding.severity == "HIGH":
                high_codes.add(code)

    return {
        "predicted_locc_failures": sorted(all_codes),
        "high_risk_codes": sorted(high_codes),
        "finding_count_by_locc_code": dict(sorted(count_by_code.items())),
    }

