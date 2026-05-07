import pathlib

from prompt_failure_analyzer.engine.analyzers.schema_risk import analyze_schema_risk
from prompt_failure_analyzer.engine.loader import load_prompt

PROMPTS = pathlib.Path(__file__).parent.parent / "fixtures" / "prompts"


def test_untyped_output_detected():
    findings = analyze_schema_risk(load_prompt(str(PROMPTS / "schema_risk.txt")))
    assert any(f.pattern == "UNTYPED_OUTPUT" for f in findings)


def test_implicit_list_detected():
    findings = analyze_schema_risk(load_prompt(str(PROMPTS / "schema_risk.txt")))
    assert any(f.pattern == "IMPLICIT_LIST" for f in findings)


def test_no_fallback_detected():
    findings = analyze_schema_risk(load_prompt(str(PROMPTS / "schema_risk.txt")))
    assert any(f.pattern == "NO_FALLBACK" for f in findings)


def test_clean_prompt_no_schema_findings():
    findings = analyze_schema_risk(load_prompt(str(PROMPTS / "clean.txt")))
    assert findings == []

