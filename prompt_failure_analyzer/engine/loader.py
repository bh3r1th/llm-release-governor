import json
from pathlib import Path

import yaml


def load_prompt(path: str) -> dict:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    content = file_path.read_text(encoding="utf-8")

    if suffix == ".txt":
        return {"system": "", "user": content}

    if suffix == ".json":
        parsed = json.loads(content)
        if "system" not in parsed or "user" not in parsed:
            raise ValueError("JSON prompt must contain 'system' and 'user' keys")
        return {"system": str(parsed["system"]), "user": str(parsed["user"])}

    if suffix in {".yaml", ".yml"}:
        parsed = yaml.safe_load(content)
        if not isinstance(parsed, dict) or "system" not in parsed or "user" not in parsed:
            raise ValueError("YAML prompt must contain 'system' and 'user' keys")
        return {"system": str(parsed["system"]), "user": str(parsed["user"])}

    raise ValueError(f"Unsupported prompt extension: {suffix}")


def prompt_to_lines(prompt: dict) -> list[str]:
    combined = f"{prompt.get('system', '')}\n{prompt.get('user', '')}"
    return combined.splitlines()

