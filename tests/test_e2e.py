import json
import pathlib
import tempfile

from click.testing import CliRunner

from release_governor.cli import cli
from release_governor.engine.loader import compute_identity_hash, load_locc_artifact

LOCC = pathlib.Path(__file__).parent / "fixtures" / "locc_artifacts"
OVERRIDES = pathlib.Path(__file__).parent / "fixtures" / "overrides"

SHA = "deadbeef"


def _invoke(*args):
    runner = CliRunner()
    return runner.invoke(cli, ["run", *args], catch_exceptions=False)


def test_e2e_allow_pass_artifact():
    result = _invoke(
        "--locc-artifact", str(LOCC / "pass.json"),
        "--env", "staging",
        "--sha", SHA,
    )
    assert result.exit_code == 0
    assert "ALLOW" in result.output


def test_e2e_block_fail_artifact():
    result = _invoke(
        "--locc-artifact", str(LOCC / "fail.json"),
        "--env", "staging",
        "--sha", SHA,
    )
    assert result.exit_code == 1
    assert "BLOCK" in result.output


def test_e2e_block_pii_no_override():
    result = _invoke(
        "--locc-artifact", str(LOCC / "pass_with_pii.json"),
        "--env", "staging",
        "--sha", SHA,
    )
    assert result.exit_code == 1
    assert "BLOCK" in result.output


def test_e2e_allow_with_valid_override():
    artifact = load_locc_artifact(str(LOCC / "pass_with_pii.json"))
    real_hash = compute_identity_hash(artifact)

    override = {
        "approved_by": "alice",
        "reason": "confirmed false positive",
        "scope": "staging",
        "expires_at": "2027-05-06T00:00:00Z",
        "approved_head_sha": SHA,
        "leakage_type": "pii",
        "identity_hash": real_hash,
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(override, f)
        override_path = f.name

    result = _invoke(
        "--locc-artifact", str(LOCC / "pass_with_pii.json"),
        "--env", "staging",
        "--sha", SHA,
        "--override-file", override_path,
    )
    assert result.exit_code == 0
    assert "ALLOW" in result.output


def test_e2e_require_override_expired():
    result = _invoke(
        "--locc-artifact", str(LOCC / "pass_with_pii.json"),
        "--env", "staging",
        "--sha", SHA,
        "--override-file", str(OVERRIDES / "expired.json"),
    )
    assert result.exit_code == 2
    assert "REQUIRE_OVERRIDE" in result.output


def test_e2e_block_preprod_hold():
    result = _invoke(
        "--locc-artifact", str(LOCC / "hold.json"),
        "--env", "preprod",
        "--sha", SHA,
    )
    assert result.exit_code == 1
    assert "BLOCK" in result.output


def test_e2e_block_prod_with_diffs():
    result = _invoke(
        "--locc-artifact", str(LOCC / "hold.json"),
        "--env", "prod",
        "--sha", SHA,
    )
    assert result.exit_code == 1
    assert "BLOCK" in result.output


def test_e2e_markdown_output():
    result = _invoke(
        "--locc-artifact", str(LOCC / "pass.json"),
        "--env", "staging",
        "--sha", SHA,
        "--output", "markdown",
    )
    assert result.exit_code == 0
    assert "## Release Governor" in result.output


def test_e2e_invalid_artifact_path():
    result = _invoke(
        "--locc-artifact", "nonexistent/path/artifact.json",
        "--env", "staging",
        "--sha", SHA,
    )
    assert result.exit_code != 0
    assert "Error" in result.output
