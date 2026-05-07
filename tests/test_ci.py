import json
import os
import pathlib
import shutil
import tempfile

from click.testing import CliRunner

from release_governor.cli import cli

CI = pathlib.Path(__file__).parent / "fixtures" / "ci"
SHA = "deadbeef"
ENV = "staging"


def _evaluate(runner, *args):
    return runner.invoke(cli, ["evaluate", *args], catch_exceptions=False)


def _make_local_test_dir() -> tuple[str, str]:
    token_dir = tempfile.mkdtemp(dir=".")
    run_dir = f"ci_run_{os.path.basename(token_dir)}"
    os.makedirs(run_dir, exist_ok=True)
    return token_dir, run_dir


def test_ci_clean_artifact_allow():
    runner = CliRunner()
    original_cwd = os.getcwd()
    tmp, run_dir = _make_local_test_dir()
    try:
        os.chdir(run_dir)
        result = _evaluate(
            runner,
            "--locc-artifact", str(CI / "clean_artifact.json"),
            "--env", ENV,
            "--sha", SHA,
        )
        assert result.exit_code == 0
        assert pathlib.Path("governor_decision.json").exists()
        decision = json.loads(pathlib.Path("governor_decision.json").read_text())
        assert decision["decision"] == "ALLOW"
    finally:
        os.chdir(original_cwd)
        shutil.rmtree(run_dir, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)


def test_ci_leakage_no_override_block():
    runner = CliRunner()
    original_cwd = os.getcwd()
    tmp, run_dir = _make_local_test_dir()
    try:
        os.chdir(run_dir)
        result = _evaluate(
            runner,
            "--locc-artifact", str(CI / "leakage_no_override.json"),
            "--env", ENV,
            "--sha", SHA,
        )
        assert result.exit_code == 1
        decision = json.loads(pathlib.Path("governor_decision.json").read_text())
        assert decision["decision"] == "BLOCK"
        assert "PROMOTION BLOCKED" in result.stderr
    finally:
        os.chdir(original_cwd)
        shutil.rmtree(run_dir, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)


def test_ci_valid_override_allow():
    bundle = CI / "valid_override_bundle"
    runner = CliRunner()
    original_cwd = os.getcwd()
    tmp, run_dir = _make_local_test_dir()
    try:
        os.chdir(run_dir)
        result = _evaluate(
            runner,
            "--locc-artifact", str(bundle / "locc_artifact.json"),
            "--env", ENV,
            "--sha", SHA,
            "--override-file", str(bundle / "override.json"),
        )
        assert result.exit_code == 0
        decision = json.loads(pathlib.Path("governor_decision.json").read_text())
        assert decision["decision"] == "ALLOW"
    finally:
        os.chdir(original_cwd)
        shutil.rmtree(run_dir, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)


def test_ci_bad_override_require_override():
    bundle = CI / "bad_override_bundle"
    runner = CliRunner()
    original_cwd = os.getcwd()
    tmp, run_dir = _make_local_test_dir()
    try:
        os.chdir(run_dir)
        result = _evaluate(
            runner,
            "--locc-artifact", str(bundle / "locc_artifact.json"),
            "--env", ENV,
            "--sha", SHA,
            "--override-file", str(bundle / "override.json"),
        )
        assert result.exit_code == 2
        decision = json.loads(pathlib.Path("governor_decision.json").read_text())
        assert decision["decision"] == "REQUIRE_OVERRIDE"
        assert "override expired" in decision["override_failures"]
    finally:
        os.chdir(original_cwd)
        shutil.rmtree(run_dir, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)


def test_ci_governor_decision_json_schema():
    runner = CliRunner()
    original_cwd = os.getcwd()
    tmp, run_dir = _make_local_test_dir()
    try:
        os.chdir(run_dir)
        _evaluate(
            runner,
            "--locc-artifact", str(CI / "clean_artifact.json"),
            "--env", ENV,
            "--sha", SHA,
        )
        decision = json.loads(pathlib.Path("governor_decision.json").read_text())
        for key in ("decision", "env", "artifact_hash", "leakage", "override_failures", "notes"):
            assert key in decision, f"Missing key: {key}"
    finally:
        os.chdir(original_cwd)
        shutil.rmtree(run_dir, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)


def test_ci_block_fails_job_exit_code():
    runner = CliRunner()
    original_cwd = os.getcwd()
    tmp, run_dir = _make_local_test_dir()
    try:
        os.chdir(run_dir)
        result = _evaluate(
            runner,
            "--locc-artifact", str(CI / "leakage_no_override.json"),
            "--env", ENV,
            "--sha", SHA,
        )
        assert result.exit_code == 1
    finally:
        os.chdir(original_cwd)
        shutil.rmtree(run_dir, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)
