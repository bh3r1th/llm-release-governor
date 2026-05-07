"""Aggregates leakage scores and override signals into a final go/no-go release decision."""

from dataclasses import dataclass, field

from release_governor.engine.audit import append_audit_log, make_audit_event
from release_governor.engine.leakage import active_leakage_types, classify_leakage
from release_governor.engine.override import is_sha_rotated, validate_override


@dataclass
class DecisionResult:
    decision: str
    leakage: dict
    override_failures: list[str]
    notes: list[str] = field(default_factory=list)


def make_decision(
    artifact: dict,
    env: str,
    sha: str,
    artifact_hash: str,
    override: dict | None = None,
    override_file: str | None = None,
    audit_log_path: str | None = None,
) -> DecisionResult:
    classification = classify_leakage(artifact, env)
    leakage_types = active_leakage_types(classification)

    if not classification["any"]:
        result = DecisionResult(
            decision="ALLOW",
            leakage=classification,
            override_failures=[],
            notes=["No leakage detected"],
        )
        _emit_audit_event(
            result, env, sha, artifact_hash, leakage_types, override, override_file, audit_log_path
        )
        return result

    if override is None:
        result = DecisionResult(
            decision="BLOCK",
            leakage=classification,
            override_failures=[],
            notes=[f"Leakage detected: {leakage_types}. No override provided."],
        )
        _emit_audit_event(
            result, env, sha, artifact_hash, leakage_types, override, override_file, audit_log_path
        )
        return result

    failures = validate_override(override, artifact_hash, env, sha, leakage_types)

    if not failures:
        result = DecisionResult(
            decision="ALLOW",
            leakage=classification,
            override_failures=[],
            notes=[f"Leakage overridden by {override['approved_by']}: {override['reason']}"],
        )
        _emit_audit_event(
            result, env, sha, artifact_hash, leakage_types, override, override_file, audit_log_path
        )
        return result

    result = DecisionResult(
        decision="REQUIRE_OVERRIDE",
        leakage=classification,
        override_failures=failures,
        notes=["Override provided but invalid. Fix failures and resubmit."],
    )
    _emit_audit_event(
        result, env, sha, artifact_hash, leakage_types, override, override_file, audit_log_path
    )
    return result


def _emit_audit_event(
    result: DecisionResult,
    env: str,
    sha: str,
    artifact_hash: str,
    leakage_types: list[str],
    override: dict | None,
    override_file: str | None,
    audit_log_path: str | None,
) -> None:
    if audit_log_path is None:
        return

    actor = override["approved_by"] if override is not None else "system"

    if result.decision == "ALLOW":
        event_type = "OVERRIDE_USED" if leakage_types else "PROMOTION_ALLOWED"
    elif result.decision == "BLOCK":
        event_type = "PROMOTION_BLOCKED"
    else:
        if result.override_failures == ["override expired"]:
            event_type = "OVERRIDE_EXPIRED"
        elif override is not None and is_sha_rotated(override, sha):
            event_type = "OVERRIDE_SHA_ROTATED"
        else:
            event_type = "OVERRIDE_REJECTED"

    event = make_audit_event(
        event_type=event_type,
        env=env,
        sha=sha,
        identity_hash=artifact_hash,
        leakage_types=leakage_types,
        actor=actor,
        override_file=override_file,
        failures=result.override_failures,
        notes=result.notes,
    )
    append_audit_log(event, audit_log_path)
