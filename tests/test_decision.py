import copy
import json
import pathlib

from release_governor.engine.loader import load_locc_artifact, load_override_file
from release_governor.engine.decision import make_decision

LOCC = pathlib.Path(__file__).parent / "fixtures" / "locc_artifacts"
OVERRIDES = pathlib.Path(__file__).parent / "fixtures" / "overrides"

ARTIFACT_HASH = "abc123"
SHA = "deadbeef"
ENV = "staging"


def _artifact(name: str) -> dict:
    return load_locc_artifact(str(LOCC / name))


def _override(name: str) -> dict:
    return load_override_file(str(OVERRIDES / name))


def _override_raw(name: str) -> dict:
    with open(OVERRIDES / name, encoding="utf-8") as f:
        return json.load(f)


def test_allow_no_leakage():
    result = make_decision(_artifact("pass.json"), ENV, SHA, ARTIFACT_HASH)
    assert result.decision == "ALLOW"
    assert result.override_failures == []


def test_block_pii_no_override():
    result = make_decision(_artifact("pass_with_pii.json"), ENV, SHA, ARTIFACT_HASH)
    assert result.decision == "BLOCK"
    assert result.override_failures == []


def test_block_policy_fail():
    result = make_decision(_artifact("fail.json"), ENV, SHA, ARTIFACT_HASH)
    assert result.decision == "BLOCK"


def test_allow_with_valid_override():
    result = make_decision(
        _artifact("pass_with_pii.json"),
        ENV,
        SHA,
        ARTIFACT_HASH,
        override=_override("valid_staging.json"),
    )
    assert result.decision == "ALLOW"
    assert result.override_failures == []


def test_require_override_expired():
    result = make_decision(
        _artifact("pass_with_pii.json"),
        ENV,
        SHA,
        ARTIFACT_HASH,
        override=_override("expired.json"),
    )
    assert result.decision == "REQUIRE_OVERRIDE"
    assert "override expired" in result.override_failures


def test_require_override_wrong_sha():
    result = make_decision(
        _artifact("pass_with_pii.json"),
        ENV,
        SHA,
        ARTIFACT_HASH,
        override=_override("wrong_sha.json"),
    )
    assert result.decision == "REQUIRE_OVERRIDE"
    assert any("approved_head_sha mismatch" in f for f in result.override_failures)


def test_block_schema_and_pii():
    artifact = copy.deepcopy(_artifact("pass_with_schema_drift.json"))
    artifact["checks"][0]["reasons"] = ["contains email address in output"]

    result = make_decision(artifact, ENV, SHA, ARTIFACT_HASH)
    assert result.decision == "BLOCK"
    assert result.leakage["pii"] is True
    assert result.leakage["schema"] is True
    assert "pii" in result.notes[0]


def test_block_multi_leakage_no_override():
    artifact = copy.deepcopy(_artifact("pass_with_schema_drift.json"))
    artifact["checks"][0]["reasons"] = ["contains email address in output"]

    result = make_decision(artifact, ENV, SHA, ARTIFACT_HASH)
    assert result.decision == "BLOCK"
    assert "pii" in result.notes[0]
    assert "schema" in result.notes[0]


def test_allow_multi_leakage_full_override():
    artifact = copy.deepcopy(_artifact("pass_with_schema_drift.json"))
    artifact["checks"][0]["reasons"] = ["contains email address in output"]

    result = make_decision(
        artifact,
        ENV,
        SHA,
        ARTIFACT_HASH,
        override=_override_raw("multi_leakage_full.json"),
    )
    assert result.decision == "ALLOW"
    assert result.override_failures == []


def test_require_override_partial_coverage():
    artifact = copy.deepcopy(_artifact("pass_with_schema_drift.json"))
    artifact["checks"][0]["reasons"] = ["contains email address in output"]

    result = make_decision(
        artifact,
        ENV,
        SHA,
        ARTIFACT_HASH,
        override=_override_raw("multi_leakage_partial.json"),
    )
    assert result.decision == "REQUIRE_OVERRIDE"
    assert any("leakage_types insufficient" in failure for failure in result.override_failures)
