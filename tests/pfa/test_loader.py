import json
import pathlib
import shutil
import tempfile

import pytest

from prompt_failure_analyzer.engine.loader import load_prompt

PROMPTS = pathlib.Path(__file__).parent.parent / "fixtures" / "prompts"


def test_load_txt():
    prompt = load_prompt(str(PROMPTS / "clean.txt"))
    assert prompt["system"] == ""
    assert len(prompt["user"]) > 0


def test_load_json():
    prompt = load_prompt(str(PROMPTS / "pii_risk.json"))
    assert "system" in prompt
    assert "user" in prompt


def test_load_yaml():
    prompt = load_prompt(str(PROMPTS / "constraint_risk.yaml"))
    assert "must always" in prompt["system"].lower()


def test_load_missing_key():
    token = tempfile.mkdtemp(dir=".")
    local_dir = pathlib.Path(f"pfa_loader_{pathlib.Path(token).name}")
    local_dir.mkdir(parents=True, exist_ok=True)
    payload = {"system": "x"}
    p = local_dir / "bad.json"
    try:
        p.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ValueError):
            load_prompt(str(p))
    finally:
        shutil.rmtree(local_dir, ignore_errors=True)
        shutil.rmtree(token, ignore_errors=True)
