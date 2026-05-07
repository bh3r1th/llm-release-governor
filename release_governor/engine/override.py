"""Loads and applies per-environment human override files to gate or force-pass release decisions."""

from datetime import datetime, timezone
import sys

_SHA_WILDCARDS = {"*", "any", "latest", ""}


def validate_override(
    override: dict,
    artifact_hash: str,
    env: str,
    sha: str,
    detected_leakage_types: list[str],
) -> list[str]:
    failures = []

    if override["identity_hash"] != artifact_hash:
        failures.append("identity_hash mismatch")

    if override["scope"] != env:
        failures.append(f"scope mismatch: expected {env}, got {override['scope']}")

    expires = datetime.fromisoformat(override["expires_at"]).replace(tzinfo=timezone.utc)
    if expires <= datetime.now(timezone.utc):
        failures.append("override expired")

    approved_head_sha = override["approved_head_sha"]
    if approved_head_sha in _SHA_WILDCARDS:
        return ["approved_head_sha wildcard not permitted"]

    if approved_head_sha != sha:
        failures.append(
            "approved_head_sha mismatch: override bound to "
            f"{approved_head_sha}, current HEAD is {sha}. "
            "Re-approve override at current SHA to continue."
        )

    override_leakage_types = override.get("leakage_types")
    if override_leakage_types is None and "leakage_type" in override:
        override_leakage_types = [override["leakage_type"]]
        print(
            "Deprecation warning: override uses 'leakage_type'; use 'leakage_types' instead.",
            file=sys.stderr,
        )

    if override_leakage_types is None:
        override_leakage_types = []

    if not set(override_leakage_types).issuperset(set(detected_leakage_types)):
        failures.append(
            "leakage_types insufficient: "
            f"override covers {override_leakage_types}, detected {detected_leakage_types}"
        )

    return failures


def is_sha_rotated(override: dict, sha: str) -> bool:
    approved_head_sha = override["approved_head_sha"]
    return approved_head_sha not in _SHA_WILDCARDS and approved_head_sha != sha
