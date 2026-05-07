import json
import pathlib
import shutil
import uuid
from datetime import UTC, datetime

from release_governor.engine.audit import (
    append_audit_log,
    make_audit_event,
    read_audit_log,
)
from release_governor.engine.decision import make_decision
from release_governor.engine.loader import load_locc_artifact, load_override_file

LOCC = pathlib.Path(__file__).parent / "fixtures" / "locc_artifacts"
OVERRIDES = pathlib.Path(__file__).parent / "fixtures" / "overrides"

ARTIFACT_HASH = "abc123"
SHA = "deadbeef"
ENV = "staging"


def _artifact(name: str) -> dict:
    return load_locc_artifact(str(LOCC / name))


def _override(name: str) -> dict:
    return load_override_file(str(OVERRIDES / name))


def _tmp_dir() -> pathlib.Path:
    path = pathlib.Path("tests") / "tmp_pytest" / f"audit_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def test_make_audit_event_fields():
    event = make_audit_event(
        event_type="PROMOTION_ALLOWED",
        env=ENV,
        sha=SHA,
        identity_hash=ARTIFACT_HASH,
        leakage_types=[],
        actor="system",
        override_file=None,
        failures=[],
        notes=["No leakage detected"],
    )
    parsed_ts = datetime.fromisoformat(event["timestamp"])
    assert parsed_ts.tzinfo == UTC
    assert event["event_type"] == "PROMOTION_ALLOWED"
    assert event["env"] == ENV
    assert event["sha"] == SHA
    assert event["identity_hash"] == ARTIFACT_HASH
    assert event["leakage_types"] == []
    assert event["actor"] == "system"
    assert event["override_file"] is None
    assert event["failures"] == []
    assert event["notes"] == ["No leakage detected"]


def test_append_creates_file():
    root = _tmp_dir()
    try:
        path = root / "audit" / "rg_audit.jsonl"
        event = make_audit_event(
            "PROMOTION_ALLOWED", ENV, SHA, ARTIFACT_HASH, [], "system", None, [], ["No leakage detected"]
        )
        append_audit_log(event, str(path))
        assert path.exists()
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_append_is_additive():
    root = _tmp_dir()
    try:
        path = root / "rg_audit.jsonl"
        e1 = make_audit_event(
            "PROMOTION_ALLOWED", ENV, SHA, ARTIFACT_HASH, [], "system", None, [], ["No leakage detected"]
        )
        e2 = make_audit_event(
            "PROMOTION_BLOCKED", ENV, SHA, ARTIFACT_HASH, ["pii"], "system", None, [], ["Leakage detected"]
        )
        append_audit_log(e1, str(path))
        append_audit_log(e2, str(path))
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        json.loads(lines[0])
        json.loads(lines[1])
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_read_audit_log_parses_events():
    root = _tmp_dir()
    try:
        path = root / "rg_audit.jsonl"
        e1 = make_audit_event(
            "PROMOTION_ALLOWED", ENV, SHA, ARTIFACT_HASH, [], "system", None, [], ["No leakage detected"]
        )
        e2 = make_audit_event(
            "PROMOTION_BLOCKED", ENV, SHA, ARTIFACT_HASH, ["pii"], "system", None, [], ["Leakage detected"]
        )
        append_audit_log(e1, str(path))
        append_audit_log(e2, str(path))
        events = read_audit_log(str(path))
        assert len(events) == 2
        assert events[0]["event_type"] == "PROMOTION_ALLOWED"
        assert events[1]["event_type"] == "PROMOTION_BLOCKED"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_audit_allow_no_leakage():
    root = _tmp_dir()
    try:
        path = root / "rg_audit.jsonl"
        make_decision(
            _artifact("pass.json"),
            ENV,
            SHA,
            ARTIFACT_HASH,
            audit_log_path=str(path),
        )
        events = read_audit_log(str(path))
        assert len(events) == 1
        assert events[0]["event_type"] == "PROMOTION_ALLOWED"
        assert events[0]["actor"] == "system"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_audit_override_used():
    root = _tmp_dir()
    try:
        path = root / "rg_audit.jsonl"
        make_decision(
            _artifact("pass_with_pii.json"),
            ENV,
            SHA,
            ARTIFACT_HASH,
            override=_override("valid_staging.json"),
            override_file=str(OVERRIDES / "valid_staging.json"),
            audit_log_path=str(path),
        )
        events = read_audit_log(str(path))
        assert len(events) == 1
        assert events[0]["event_type"] == "OVERRIDE_USED"
        assert events[0]["actor"] == "alice"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_audit_override_expired():
    root = _tmp_dir()
    try:
        path = root / "rg_audit.jsonl"
        make_decision(
            _artifact("pass_with_pii.json"),
            ENV,
            SHA,
            ARTIFACT_HASH,
            override=_override("expired.json"),
            override_file=str(OVERRIDES / "expired.json"),
            audit_log_path=str(path),
        )
        events = read_audit_log(str(path))
        assert len(events) == 1
        assert events[0]["event_type"] == "OVERRIDE_EXPIRED"
        assert events[0]["failures"] == ["override expired"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_audit_sha_rotated_event():
    root = _tmp_dir()
    try:
        path = root / "rg_audit.jsonl"
        make_decision(
            _artifact("pass_with_pii.json"),
            ENV,
            SHA,
            ARTIFACT_HASH,
            override=_override("rotated_sha.json"),
            override_file=str(OVERRIDES / "rotated_sha.json"),
            audit_log_path=str(path),
        )
        events = read_audit_log(str(path))
        assert len(events) == 1
        assert events[0]["event_type"] == "OVERRIDE_SHA_ROTATED"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_audit_wildcard_sha_emits_rejected():
    root = _tmp_dir()
    try:
        path = root / "rg_audit.jsonl"
        make_decision(
            _artifact("pass_with_pii.json"),
            ENV,
            SHA,
            ARTIFACT_HASH,
            override=_override("wildcard_sha.json"),
            override_file=str(OVERRIDES / "wildcard_sha.json"),
            audit_log_path=str(path),
        )
        events = read_audit_log(str(path))
        assert len(events) == 1
        assert events[0]["event_type"] == "OVERRIDE_REJECTED"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_audit_rotated_sha_actor_preserved():
    root = _tmp_dir()
    try:
        path = root / "rg_audit.jsonl"
        make_decision(
            _artifact("pass_with_pii.json"),
            ENV,
            SHA,
            ARTIFACT_HASH,
            override=_override("rotated_sha.json"),
            override_file=str(OVERRIDES / "rotated_sha.json"),
            audit_log_path=str(path),
        )
        events = read_audit_log(str(path))
        assert len(events) == 1
        assert events[0]["event_type"] == "OVERRIDE_SHA_ROTATED"
        assert events[0]["actor"] == "alice"
    finally:
        shutil.rmtree(root, ignore_errors=True)
