"""Detects prompt-leakage and sensitive-data exposure risk in LLM change manifests."""

PII_KEYWORDS = [
    "email", "ssn", "phone", "address", "dob",
    "date of birth", "social security", "credit card",
]

SCHEMA_CHANGE_TYPES = {"missing", "type_changed", "enum_drift"}


def detect_pii_leakage(artifact: dict) -> bool:
    for check in artifact["checks"]:
        for reason in check["reasons"]:
            lower = reason.lower()
            if any(kw in lower for kw in PII_KEYWORDS):
                return True
    return False


def detect_schema_leakage(artifact: dict) -> bool:
    for check in artifact["checks"]:
        for diff in check["diffs"]:
            if diff["change_type"] in SCHEMA_CHANGE_TYPES:
                return True
    return False


def detect_policy_leakage(artifact: dict, env: str) -> bool:
    status = artifact["status"]

    if env == "staging":
        return status == "FAIL"

    if env == "preprod":
        return status in {"FAIL", "HOLD"}

    if env == "prod":
        if status != "PASS":
            return True
        return any(
            diff
            for check in artifact["checks"]
            for diff in check["diffs"]
        )

    return False


def classify_leakage(artifact: dict, env: str) -> dict:
    pii = detect_pii_leakage(artifact)
    schema = detect_schema_leakage(artifact)
    policy = detect_policy_leakage(artifact, env)
    return {
        "pii": pii,
        "schema": schema,
        "policy": policy,
        "any": pii or schema or policy,
    }


def primary_leakage_type(classification: dict) -> str | None:
    for leakage_type in ("pii", "schema", "policy"):
        if classification[leakage_type]:
            return leakage_type
    return None


def active_leakage_types(classification: dict) -> list[str]:
    return sorted(
        leakage_type
        for leakage_type in ("pii", "schema", "policy")
        if classification.get(leakage_type, False)
    )
