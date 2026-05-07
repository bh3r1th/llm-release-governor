import json
import pathlib
from datetime import datetime, timedelta, timezone

BASE_DIR = "overrides"
_REQUIRED_KEYS = {
    "approved_by",
    "reason",
    "scope",
    "expires_at",
    "approved_head_sha",
    "leakage_types",
    "identity_hash",
}
_SHA_WILDCARDS = {"*", "any", "latest", ""}


def _parse_iso8601(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def create_override(
    env: str,
    approved_by: str,
    reason: str,
    leakage_types: list[str],
    sha: str,
    identity_hash: str,
    expires_in_days: int,
    filename: str | None = None,
) -> pathlib.Path:
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(days=expires_in_days)).isoformat()
    override = {
        "approved_by": approved_by,
        "reason": reason,
        "scope": env,
        "expires_at": expires_at,
        "approved_head_sha": sha,
        "leakage_types": leakage_types,
        "identity_hash": identity_hash,
    }

    if filename is None:
        filename = f"{env}-{sha[:8]}-{int(now.timestamp())}.json"

    path = pathlib.Path(BASE_DIR) / env / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(override, indent=2), encoding="utf-8")
    return path


def list_overrides(env: str | None = None) -> list[dict]:
    root = pathlib.Path(BASE_DIR)
    pattern = f"{env}/*.json" if env is not None else "*/*.json"

    entries: list[dict] = []
    for file_path in root.glob(pattern):
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            payload["_path"] = str(file_path)
            missing = [key for key in _REQUIRED_KEYS if key not in payload]
            if missing:
                payload["_status"] = "invalid"
            else:
                expires_at = _parse_iso8601(payload["expires_at"])
                if expires_at <= datetime.now(timezone.utc):
                    payload["_status"] = "expired"
                elif payload["approved_head_sha"] in _SHA_WILDCARDS:
                    payload["_status"] = "invalid"
                else:
                    payload["_status"] = "active"
        except Exception:
            payload = {"_path": str(file_path), "_status": "invalid"}
        entries.append(payload)

    def _sort_key(item: dict) -> tuple[int, datetime]:
        if item.get("_status") == "invalid":
            return (1, datetime.max.replace(tzinfo=timezone.utc))
        try:
            return (0, _parse_iso8601(item["expires_at"]))
        except Exception:
            return (1, datetime.max.replace(tzinfo=timezone.utc))

    entries.sort(key=_sort_key)
    return entries


def expire_override(path: str) -> None:
    file_path = pathlib.Path(path)
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    payload["expires_at"] = datetime.now(timezone.utc).isoformat()
    file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def validate_override_file(path: str) -> list[str]:
    errors: list[str] = []

    try:
        payload = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        return [f"invalid JSON: {e}"]

    for key in sorted(_REQUIRED_KEYS):
        if key not in payload:
            errors.append(f"missing required key: {key}")

    leakage_types = payload.get("leakage_types")
    if "leakage_types" in payload and (
        not isinstance(leakage_types, list) or len(leakage_types) == 0
    ):
        errors.append("leakage_types must be a non-empty list")

    approved_head_sha = payload.get("approved_head_sha")
    if "approved_head_sha" in payload and approved_head_sha in _SHA_WILDCARDS:
        errors.append("approved_head_sha wildcard not permitted")

    expires_at = payload.get("expires_at")
    if "expires_at" in payload:
        try:
            _parse_iso8601(expires_at)
        except Exception:
            errors.append("expires_at must be valid ISO 8601")

    return errors
