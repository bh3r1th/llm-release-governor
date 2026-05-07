import json
from unittest.mock import MagicMock, patch

from release_governor.engine.decision import DecisionResult
from release_governor.reporters.github_reporter import (
    load_pfa_summary,
    post_pr_comment,
    render_pr_comment,
)

_ALLOW = DecisionResult(
    decision="ALLOW",
    leakage={"pii": False, "schema": False, "policy": False, "any": False},
    override_failures=[],
    notes=["No leakage detected"],
)

_BLOCK = DecisionResult(
    decision="BLOCK",
    leakage={"pii": True, "schema": False, "policy": False, "any": True},
    override_failures=[],
    notes=["Leakage detected: pii. No override provided."],
)

_REQUIRE_OVERRIDE = DecisionResult(
    decision="REQUIRE_OVERRIDE",
    leakage={"pii": True, "schema": False, "policy": False, "any": True},
    override_failures=["override expired", "identity_hash mismatch"],
    notes=["Override provided but invalid. Fix failures and resubmit."],
)

_HASH = "abc123"
_ENV = "staging"
_PATH = "governor_decision.json"


def test_render_allow_comment():
    body = render_pr_comment(_ALLOW, _HASH, _ENV, _PATH)
    assert "✅ ALLOW" in body
    assert "Override Failures" not in body


def test_render_block_comment():
    body = render_pr_comment(_BLOCK, _HASH, _ENV, _PATH)
    assert "🚫 BLOCK" in body
    assert "PII: 🚫" in body


def test_render_require_override_comment():
    body = render_pr_comment(_REQUIRE_OVERRIDE, _HASH, _ENV, _PATH)
    assert "⚠️ REQUIRE_OVERRIDE" in body
    assert "### Override Failures" in body
    assert f"overrides/{_ENV}/active.json" in body


def test_render_artifact_path_in_comment():
    body = render_pr_comment(_ALLOW, _HASH, _ENV, _PATH)
    assert _PATH in body


def test_post_pr_comment_success():
    mock_response = MagicMock()
    mock_response.status_code = 201
    with patch("release_governor.reporters.github_reporter.requests.post", return_value=mock_response):
        post_pr_comment("body text", "owner/repo", 42, "token123")


def test_post_pr_comment_failure():
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"
    with patch("release_governor.reporters.github_reporter.requests.post", return_value=mock_response):
        try:
            post_pr_comment("body text", "owner/repo", 42, "bad_token")
            assert False, "Expected RuntimeError"
        except RuntimeError as e:
            assert "403" in str(e)


def test_render_comment_with_pfa_summary():
    pfa_summary = {
        "total": 3,
        "high": 2,
        "medium": 1,
        "low": 0,
        "passed": False,
        "locc_risk": {
            "predicted_locc_failures": ["pii.direct_exposure", "contract.pii_policy"],
            "high_risk_codes": ["pii.direct_exposure"],
            "finding_count_by_locc_code": {"pii.direct_exposure": 1, "contract.pii_policy": 2},
        },
    }
    body = render_pr_comment(_BLOCK, _HASH, _ENV, _PATH, pfa_summary)
    assert "### PFA Pre-flight" in body
    assert "2 HIGH" in body
    assert "pii.direct_exposure" in body


def test_render_comment_without_pfa_summary():
    body = render_pr_comment(_BLOCK, _HASH, _ENV, _PATH, None)
    assert "### PFA Pre-flight" not in body


def test_render_pfa_passed_shows_checkmark():
    pfa_summary = {
        "total": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "passed": True,
        "locc_risk": {"predicted_locc_failures": [], "high_risk_codes": [], "finding_count_by_locc_code": {}},
    }
    body = render_pr_comment(_ALLOW, _HASH, _ENV, _PATH, pfa_summary)
    assert "✅ Passed" in body


def test_render_pfa_failed_shows_block():
    pfa_summary = {
        "total": 1,
        "high": 1,
        "medium": 0,
        "low": 0,
        "passed": False,
        "locc_risk": {"predicted_locc_failures": ["x"], "high_risk_codes": ["x"], "finding_count_by_locc_code": {"x": 1}},
    }
    body = render_pr_comment(_BLOCK, _HASH, _ENV, _PATH, pfa_summary)
    assert "🚫 Failed" in body


def test_load_pfa_summary_missing_file():
    assert load_pfa_summary("nonexistent.json") is None
