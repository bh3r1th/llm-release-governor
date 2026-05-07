import pathlib

from prompt_failure_analyzer.engine.analyzers.pii_risk import analyze_pii_risk
from prompt_failure_analyzer.engine.loader import load_prompt

PROMPTS = pathlib.Path(__file__).parent.parent / "fixtures" / "prompts"


def test_pii_field_detected():
    findings = analyze_pii_risk(load_prompt(str(PROMPTS / "pii_risk.json")))
    pii = [f for f in findings if f.pattern == "PII_FIELD_REQUESTED"]
    assert len(pii) == 2


def test_pii_line_number_set():
    findings = analyze_pii_risk(load_prompt(str(PROMPTS / "pii_risk.json")))
    pii = [f for f in findings if f.pattern == "PII_FIELD_REQUESTED"]
    assert all(f.line is not None for f in pii)


def test_user_data_passthrough_detected():
    findings = analyze_pii_risk(load_prompt(str(PROMPTS / "pii_risk.json")))
    assert any(f.pattern == "USER_DATA_PASSTHROUGH" for f in findings)


def test_clean_prompt_no_pii_findings():
    findings = analyze_pii_risk(load_prompt(str(PROMPTS / "clean.txt")))
    assert findings == []

