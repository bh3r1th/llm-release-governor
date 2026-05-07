import json
import pathlib
import pytest
import tempfile

from release_governor.engine.loader import (
    compute_identity_hash,
    load_locc_artifact,
    load_override_file,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
LOCC = FIXTURES / "locc_artifacts"
OVERRIDES = FIXTURES / "overrides"


def test_load_locc_pass():
    artifact = load_locc_artifact(str(LOCC / "pass.json"))
    assert artifact["status"] == "PASS"


def test_load_locc_fail():
    artifact = load_locc_artifact(str(LOCC / "fail.json"))
    assert artifact["status"] == "FAIL"


def test_load_locc_invalid_json():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json {{")
        path = f.name
    with pytest.raises(ValueError):
        load_locc_artifact(path)


def test_compute_identity_hash_deterministic():
    artifact = {"version": "1.1.0", "status": "PASS", "checks": []}
    h1 = compute_identity_hash(artifact)
    h2 = compute_identity_hash(artifact)
    assert h1 == h2

    reordered = {"checks": [], "status": "PASS", "version": "1.1.0"}
    assert compute_identity_hash(reordered) == h1


def test_load_override_valid():
    data = {
        "approved_by": "alice",
        "reason": "test",
        "scope": "staging",
        "expires_at": "2027-05-06T00:00:00Z",
        "approved_head_sha": "deadbeef",
        "leakage_types": ["pii"],
        "identity_hash": "abc123",
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name
    override = load_override_file(path)
    assert override["approved_by"] == "alice"


def test_load_override_missing_key():
    data = {
        "approved_by": "alice",
        "reason": "test",
        "expires_at": "2027-05-06T00:00:00Z",
        "approved_head_sha": "deadbeef",
        "leakage_types": ["pii"],
        "identity_hash": "abc123",
        # "scope" intentionally omitted
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name
    with pytest.raises(ValueError):
        load_override_file(path)


def test_load_override_with_leakage_types_plural():
    data = {
        "approved_by": "alice",
        "reason": "test",
        "scope": "staging",
        "expires_at": "2027-05-06T00:00:00Z",
        "approved_head_sha": "deadbeef",
        "leakage_types": ["pii", "schema"],
        "identity_hash": "abc123",
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name
    override = load_override_file(path)
    assert override["leakage_types"] == ["pii", "schema"]


def test_load_override_missing_leakage_types():
    data = {
        "approved_by": "alice",
        "reason": "test",
        "scope": "staging",
        "expires_at": "2027-05-06T00:00:00Z",
        "approved_head_sha": "deadbeef",
        "identity_hash": "abc123",
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name
    with pytest.raises(ValueError):
        load_override_file(path)
