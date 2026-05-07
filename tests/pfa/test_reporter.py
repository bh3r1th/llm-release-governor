import json

from prompt_failure_analyzer.engine.analyzers import Finding
from prompt_failure_analyzer.engine.reporter import build_summary, render_json, render_markdown


def test_render_json_structure():
    findings = [
        Finding("pii_risk", "HIGH", "PII_FIELD_REQUESTED", "msg", 1),
    ]
    summary = build_summary(findings)
    rendered = render_json(findings, summary, "x.txt")
    payload = json.loads(rendered)
    assert "version" in payload
    assert "summary" in payload
    assert "findings" in payload


def test_json_includes_locc_risk_key():
    findings = [Finding("pii_risk", "HIGH", "PII_FIELD_REQUESTED", "msg", 1)]
    summary = build_summary(findings)
    payload = json.loads(render_json(findings, summary, "x.txt"))
    assert "locc_risk" in payload


def test_json_findings_include_predicted_failures():
    findings = [Finding("pii_risk", "HIGH", "PII_FIELD_REQUESTED", "msg", 1)]
    summary = build_summary(findings)
    payload = json.loads(render_json(findings, summary, "x.txt"))
    assert "predicted_locc_failures" in payload["findings"][0]


def test_render_markdown_passed():
    summary = build_summary([])
    rendered = render_markdown([], summary, "x.txt")
    assert "✅" in rendered


def test_render_markdown_failed():
    findings = [Finding("schema_risk", "HIGH", "UNTYPED_OUTPUT", "msg", None)]
    summary = build_summary(findings)
    rendered = render_markdown(findings, summary, "x.txt")
    assert "🚫" in rendered


def test_markdown_includes_locc_risk_section():
    findings = [Finding("pii_risk", "HIGH", "PII_FIELD_REQUESTED", "msg", 1)]
    summary = build_summary(findings)
    rendered = render_markdown(findings, summary, "x.txt")
    assert "### locc Risk Summary" in rendered
