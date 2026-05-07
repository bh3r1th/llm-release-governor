from prompt_failure_analyzer.engine.analyzers import Finding
from prompt_failure_analyzer.engine.mapping import (
    annotate_findings,
    get_locc_codes,
    summarize_locc_risk,
)


def test_known_pattern_returns_codes():
    assert get_locc_codes("UNTYPED_OUTPUT") == [
        "schema.type_mismatch",
        "schema.missing_field",
    ]


def test_unknown_pattern_returns_empty():
    assert get_locc_codes("NOT_A_PATTERN") == []


def test_annotate_findings_adds_locc_codes():
    finding = Finding("pii_risk", "HIGH", "PII_FIELD_REQUESTED", "m", 1)
    annotated = annotate_findings([finding])[0]
    assert annotated["predicted_locc_failures"] == [
        "pii.direct_exposure",
        "contract.pii_policy",
    ]


def test_annotate_findings_unknown_pattern():
    finding = Finding("x", "LOW", "UNKNOWN", "m", None)
    annotated = annotate_findings([finding])[0]
    assert annotated["predicted_locc_failures"] == []


def test_summarize_locc_risk_unique_codes():
    findings = [
        Finding("pii_risk", "HIGH", "PII_FIELD_REQUESTED", "m", 1),
        Finding("pii_risk", "MEDIUM", "USER_DATA_PASSTHROUGH", "m", 1),
    ]
    summary = summarize_locc_risk(findings)
    assert summary["predicted_locc_failures"].count("contract.pii_policy") == 1


def test_summarize_high_risk_codes_only():
    findings = [
        Finding("pii_risk", "HIGH", "PII_FIELD_REQUESTED", "m", 1),
        Finding("pii_risk", "LOW", "REFLECT_INPUT", "m", 1),
    ]
    summary = summarize_locc_risk(findings)
    assert "pii.direct_exposure" in summary["high_risk_codes"]
    assert "pii.indirect_exposure" not in summary["high_risk_codes"]


def test_summarize_finding_count_by_code():
    findings = [
        Finding("pii_risk", "HIGH", "PII_FIELD_REQUESTED", "m", 1),
        Finding("pii_risk", "MEDIUM", "USER_DATA_PASSTHROUGH", "m", 1),
    ]
    summary = summarize_locc_risk(findings)
    assert summary["finding_count_by_locc_code"]["contract.pii_policy"] == 2

