import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta, timezone

from release_governor.engine import override_manager as om

_LOCAL_TMP_ROOT = "."


def _set_base_dir(monkeypatch, tmp: str):
    token = os.path.basename(tmp)
    monkeypatch.setattr(om, "BASE_DIR", os.path.join(".", f"overrides_test_{token}"))


def test_create_override_writes_file(monkeypatch):
    tmp = tempfile.mkdtemp(dir=_LOCAL_TMP_ROOT)
    try:
        _set_base_dir(monkeypatch, tmp)
        path = om.create_override(
            env="staging",
            approved_by="alice",
            reason="confirmed false positive",
            leakage_types=["pii"],
            sha="deadbeef",
            identity_hash="abc123",
            expires_in_days=7,
        )
        assert path.exists()
        payload = json.loads(path.read_text(encoding="utf-8"))
        for key in (
            "approved_by",
            "reason",
            "scope",
            "expires_at",
            "approved_head_sha",
            "leakage_types",
            "identity_hash",
        ):
            assert key in payload
    finally:
        shutil.rmtree(om.BASE_DIR, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)


def test_create_override_default_filename(monkeypatch):
    tmp = tempfile.mkdtemp(dir=_LOCAL_TMP_ROOT)
    try:
        _set_base_dir(monkeypatch, tmp)
        path = om.create_override(
            env="staging",
            approved_by="alice",
            reason="r",
            leakage_types=["pii"],
            sha="deadbeef1234",
            identity_hash="abc123",
            expires_in_days=7,
        )
        assert "staging-deadbeef-" in path.name
    finally:
        shutil.rmtree(om.BASE_DIR, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)


def test_create_override_expires_in_future(monkeypatch):
    tmp = tempfile.mkdtemp(dir=_LOCAL_TMP_ROOT)
    try:
        _set_base_dir(monkeypatch, tmp)
        before = datetime.now(timezone.utc)
        path = om.create_override(
            env="staging",
            approved_by="alice",
            reason="r",
            leakage_types=["pii"],
            sha="deadbeef",
            identity_hash="abc123",
            expires_in_days=7,
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        expires_at = datetime.fromisoformat(payload["expires_at"])
        expected = before + timedelta(days=7)
        assert abs((expires_at - expected).total_seconds()) <= 60
    finally:
        shutil.rmtree(om.BASE_DIR, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)


def test_list_overrides_all_envs(monkeypatch):
    tmp = tempfile.mkdtemp(dir=_LOCAL_TMP_ROOT)
    try:
        _set_base_dir(monkeypatch, tmp)
        om.create_override("staging", "alice", "r", ["pii"], "deadbeef", "a1", 7, "one.json")
        om.create_override("staging", "alice", "r", ["pii"], "deadbeef", "a2", 7, "two.json")
        om.create_override("preprod", "alice", "r", ["pii"], "deadbeef", "a3", 7, "three.json")
        assert len(om.list_overrides(env=None)) == 3
    finally:
        shutil.rmtree(om.BASE_DIR, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)


def test_list_overrides_filtered_by_env(monkeypatch):
    tmp = tempfile.mkdtemp(dir=_LOCAL_TMP_ROOT)
    try:
        _set_base_dir(monkeypatch, tmp)
        om.create_override("staging", "alice", "r", ["pii"], "deadbeef", "a1", 7, "one.json")
        om.create_override("staging", "alice", "r", ["pii"], "deadbeef", "a2", 7, "two.json")
        om.create_override("preprod", "alice", "r", ["pii"], "deadbeef", "a3", 7, "three.json")
        assert len(om.list_overrides(env="staging")) == 2
    finally:
        shutil.rmtree(om.BASE_DIR, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)


def test_list_overrides_status_active(monkeypatch):
    tmp = tempfile.mkdtemp(dir=_LOCAL_TMP_ROOT)
    try:
        _set_base_dir(monkeypatch, tmp)
        om.create_override("staging", "alice", "r", ["pii"], "deadbeef", "a1", 7, "one.json")
        rows = om.list_overrides(env="staging")
        assert rows[0]["_status"] == "active"
    finally:
        shutil.rmtree(om.BASE_DIR, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)


def test_list_overrides_status_expired(monkeypatch):
    tmp = tempfile.mkdtemp(dir=_LOCAL_TMP_ROOT)
    try:
        _set_base_dir(monkeypatch, tmp)
        path = om.create_override("staging", "alice", "r", ["pii"], "deadbeef", "a1", 7, "one.json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["expires_at"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        rows = om.list_overrides(env="staging")
        assert rows[0]["_status"] == "expired"
    finally:
        shutil.rmtree(om.BASE_DIR, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)


def test_expire_override_sets_past_timestamp(monkeypatch):
    tmp = tempfile.mkdtemp(dir=_LOCAL_TMP_ROOT)
    try:
        _set_base_dir(monkeypatch, tmp)
        path = om.create_override("staging", "alice", "r", ["pii"], "deadbeef", "a1", 7, "one.json")
        om.expire_override(str(path))
        payload = json.loads(path.read_text(encoding="utf-8"))
        expires_at = datetime.fromisoformat(payload["expires_at"])
        assert expires_at <= datetime.now(timezone.utc)
        assert path.exists()
    finally:
        shutil.rmtree(om.BASE_DIR, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)


def test_validate_override_file_valid(monkeypatch):
    tmp = tempfile.mkdtemp(dir=_LOCAL_TMP_ROOT)
    try:
        _set_base_dir(monkeypatch, tmp)
        path = om.create_override("staging", "alice", "r", ["pii"], "deadbeef", "a1", 7, "one.json")
        assert om.validate_override_file(str(path)) == []
    finally:
        shutil.rmtree(om.BASE_DIR, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)


def test_validate_override_file_errors(monkeypatch):
    tmp = tempfile.mkdtemp(dir=_LOCAL_TMP_ROOT)
    try:
        _set_base_dir(monkeypatch, tmp)
        path = os.path.join(om.BASE_DIR, "staging", "bad.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = {
            "approved_by": "alice",
            "scope": "staging",
            "expires_at": "2027-05-06T00:00:00Z",
            "approved_head_sha": "*",
            "leakage_types": ["pii"],
            "identity_hash": "abc123",
        }
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(payload, indent=2))
        errors = om.validate_override_file(str(path))
        assert "missing required key: reason" in errors
        assert "approved_head_sha wildcard not permitted" in errors
    finally:
        shutil.rmtree(om.BASE_DIR, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)
