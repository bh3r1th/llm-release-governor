import pathlib
import json
import pytest

from release_governor.engine.loader import load_override_file
from release_governor.engine.override import is_sha_rotated, validate_override

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
OVERRIDES = FIXTURES / "overrides"

IDENTITY_HASH = "abc123"
SHA = "deadbeef"
ENV = "staging"
LEAKAGE_TYPES = ["pii"]


def _load(name: str) -> dict:
    return load_override_file(str(OVERRIDES / name))


def test_override_all_pass():
    override = _load("valid_staging.json")
    failures = validate_override(override, IDENTITY_HASH, ENV, SHA, LEAKAGE_TYPES)
    assert failures == []


def test_override_expired():
    override = _load("expired.json")
    failures = validate_override(override, IDENTITY_HASH, ENV, SHA, LEAKAGE_TYPES)
    assert failures == ["override expired"]


def test_override_wrong_sha():
    override = _load("wrong_sha.json")
    failures = validate_override(override, IDENTITY_HASH, ENV, SHA, LEAKAGE_TYPES)
    assert len(failures) == 1
    assert failures[0].startswith("approved_head_sha mismatch:")


def test_override_wrong_scope():
    override = _load("wrong_scope.json")
    failures = validate_override(override, IDENTITY_HASH, ENV, SHA, LEAKAGE_TYPES)
    assert len(failures) == 1
    assert failures[0].startswith("scope mismatch:")


def test_override_multiple_failures():
    override = _load("valid_staging.json")
    # Patch in-memory: wrong sha + expired
    override = {**override, "approved_head_sha": "000000", "expires_at": "2020-01-01T00:00:00Z"}
    failures = validate_override(override, IDENTITY_HASH, ENV, SHA, LEAKAGE_TYPES)
    assert "override expired" in failures
    assert any(failure.startswith("approved_head_sha mismatch:") for failure in failures)
    assert len(failures) == 2


def _load_raw(name: str) -> dict:
    with open(OVERRIDES / name, encoding="utf-8") as f:
        return json.load(f)


def test_multi_leakage_full_override_passes():
    override = _load_raw("multi_leakage_full.json")
    failures = validate_override(override, IDENTITY_HASH, ENV, SHA, ["pii", "schema"])
    assert failures == []


def test_multi_leakage_partial_override_fails():
    override = _load_raw("multi_leakage_partial.json")
    failures = validate_override(override, IDENTITY_HASH, ENV, SHA, ["pii", "schema"])
    assert any("leakage_types insufficient" in failure for failure in failures)


def test_single_type_only_detected_full_override():
    override = _load_raw("multi_leakage_full.json")
    failures = validate_override(override, IDENTITY_HASH, ENV, SHA, ["pii"])
    assert failures == []


def test_legacy_singular_leakage_type_compat(capsys):
    override = _load_raw("legacy_single_type.json")
    failures = validate_override(override, IDENTITY_HASH, ENV, SHA, ["pii"])
    captured = capsys.readouterr()
    assert failures == []
    assert "Deprecation warning" in captured.err


def test_wildcard_sha_blocked():
    override = _load("wildcard_sha.json")
    failures = validate_override(override, IDENTITY_HASH, ENV, SHA, ["pii", "schema"])
    assert failures == ["approved_head_sha wildcard not permitted"]


@pytest.mark.parametrize("wildcard_sha", ["*", "any", "latest", ""])
def test_wildcard_variants_blocked(wildcard_sha: str):
    override = _load("valid_staging.json")
    override["approved_head_sha"] = wildcard_sha
    failures = validate_override(override, IDENTITY_HASH, ENV, SHA, ["pii", "schema"])
    assert failures == ["approved_head_sha wildcard not permitted"]


def test_rotated_sha_blocked():
    override = _load("rotated_sha.json")
    failures = validate_override(override, IDENTITY_HASH, ENV, SHA, ["pii"])
    assert any("Re-approve override at current SHA to continue." in failure for failure in failures)


def test_rotated_sha_detection():
    assert is_sha_rotated(_load("rotated_sha.json"), SHA) is True
    assert is_sha_rotated(_load("valid_staging.json"), SHA) is False


def test_exact_sha_match_passes_rule_4():
    override = _load("valid_staging.json")
    failures = validate_override(override, IDENTITY_HASH, ENV, SHA, ["pii"])
    assert not any(failure.startswith("approved_head_sha mismatch") for failure in failures)
