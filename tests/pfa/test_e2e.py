import json
import os
import pathlib
import shutil
import tempfile

from click.testing import CliRunner

from prompt_failure_analyzer.cli import cli

PROMPTS = pathlib.Path(__file__).parent.parent / "fixtures" / "prompts"


def test_e2e_clean_exits_0():
    runner = CliRunner()
    result = runner.invoke(cli, ["analyze", "--prompt", str(PROMPTS / "clean.txt")])
    assert result.exit_code == 0


def test_e2e_pii_risk_exits_1():
    runner = CliRunner()
    result = runner.invoke(cli, ["analyze", "--prompt", str(PROMPTS / "pii_risk.json")])
    assert result.exit_code == 1


def test_e2e_json_output():
    runner = CliRunner()
    result = runner.invoke(cli, ["analyze", "--prompt", str(PROMPTS / "pii_risk.json")])
    payload = json.loads(result.output)
    assert "findings" in payload


def test_e2e_out_file_written():
    runner = CliRunner()
    token = tempfile.mkdtemp(dir=".")
    out_dir = f"pfa_out_{os.path.basename(token)}"
    os.makedirs(out_dir, exist_ok=True)
    try:
        out_file = pathlib.Path(out_dir) / "pfa_out.json"
        result = runner.invoke(
            cli,
            [
                "analyze",
                "--prompt",
                str(PROMPTS / "clean.txt"),
                "--out-file",
                str(out_file),
            ],
        )
        assert result.exit_code == 0
        assert out_file.exists()
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)
        shutil.rmtree(token, ignore_errors=True)
