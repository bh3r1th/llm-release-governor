import pathlib

from prompt_failure_analyzer.engine.analyzers.constraint_risk import analyze_constraint_risk
from prompt_failure_analyzer.engine.loader import load_prompt

PROMPTS = pathlib.Path(__file__).parent.parent / "fixtures" / "prompts"


def test_ambiguous_constraint_detected():
    findings = analyze_constraint_risk(load_prompt(str(PROMPTS / "constraint_risk.yaml")))
    assert any(f.pattern == "AMBIGUOUS_CONSTRAINT" for f in findings)


def test_conflicting_instructions_detected():
    findings = analyze_constraint_risk(load_prompt(str(PROMPTS / "constraint_risk.yaml")))
    assert any(f.pattern == "CONFLICTING_INSTRUCTIONS" for f in findings)


def test_undefined_term_detected():
    prompt = {"system": "", "user": "Provide an appropriate response."}
    findings = analyze_constraint_risk(prompt)
    assert any(f.pattern == "UNDEFINED_TERM" for f in findings)


def test_clean_prompt_no_constraint_findings():
    findings = analyze_constraint_risk(load_prompt(str(PROMPTS / "clean.txt")))
    assert findings == []

