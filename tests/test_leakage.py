import pathlib

from release_governor.engine.loader import load_locc_artifact
from release_governor.engine.leakage import (
    classify_leakage,
    detect_pii_leakage,
    detect_schema_leakage,
    detect_policy_leakage,
    primary_leakage_type,
)

LOCC = pathlib.Path(__file__).parent / "fixtures" / "locc_artifacts"


def _load(name: str) -> dict:
    return load_locc_artifact(str(LOCC / name))


def test_no_leakage_pass():
    artifact = _load("pass.json")
    result = classify_leakage(artifact, "staging")
    assert result["pii"] is False
    assert result["schema"] is False
    assert result["policy"] is False
    assert result["any"] is False


def test_pii_leakage_detected():
    artifact = _load("pass_with_pii.json")
    assert detect_pii_leakage(artifact) is True


def test_schema_leakage_detected():
    artifact = _load("pass_with_schema_drift.json")
    assert detect_schema_leakage(artifact) is True


def test_policy_staging_fail():
    artifact = _load("fail.json")
    assert detect_policy_leakage(artifact, "staging") is True


def test_policy_staging_hold_no_schema():
    artifact = _load("hold.json")
    assert detect_schema_leakage(artifact) is False
    assert detect_policy_leakage(artifact, "staging") is False


def test_policy_preprod_hold():
    artifact = _load("hold.json")
    assert detect_policy_leakage(artifact, "preprod") is True


def test_policy_prod_pass_with_diffs():
    artifact = _load("hold.json")
    assert detect_policy_leakage(artifact, "prod") is True


def test_primary_leakage_type_priority():
    classification = {"pii": True, "schema": True, "policy": True, "any": True}
    assert primary_leakage_type(classification) == "pii"
