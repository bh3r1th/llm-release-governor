import pathlib
import subprocess
import sys
import tempfile

AUDIT_LOG = str(pathlib.Path(tempfile.gettempdir()) / "demo_audit.jsonl")


def run(cmd: list[str], check: bool = True) -> int:
    result = subprocess.run(cmd, check=False)
    if check and result.returncode not in (0, 1):
        sys.exit(result.returncode)
    return result.returncode


def print_audit_log() -> None:
    try:
        print(pathlib.Path(AUDIT_LOG).read_text(encoding="utf-8"))
    except FileNotFoundError:
        print("(audit log not found)")


def main() -> None:
    print("=== LLM Reliability Stack Demo ===")
    print("")

    print("--- Act 1: PFA analysis of bad prompt ---")
    run(
        [
            sys.executable,
            "-m",
            "prompt_failure_analyzer",
            "analyze",
            "--prompt",
            "demo/prompts/bad_prompt.txt",
            "--output",
            "markdown",
        ]
    )

    print("")
    print("--- Act 2: Release Governor gates bad artifact ---")
    run(
        [
            sys.executable,
            "-m",
            "release_governor",
            "evaluate",
            "--locc-artifact",
            "demo/fixtures/locc_bad.json",
            "--env",
            "staging",
            "--sha",
            "deadbeef",
            "--audit-log",
            AUDIT_LOG,
        ],
        check=False,
    )

    print("")
    print("--- Audit log after block ---")
    print_audit_log()

    print("")
    print("--- Act 3: Override path ---")
    run(
        [
            sys.executable,
            "-m",
            "release_governor",
            "evaluate",
            "--locc-artifact",
            "demo/fixtures/locc_bad.json",
            "--env",
            "staging",
            "--sha",
            "deadbeef",
            "--override-file",
            "demo/fixtures/override_demo.json",
            "--audit-log",
            AUDIT_LOG,
        ]
    )

    print("")
    print("--- Audit log after override ---")
    print_audit_log()

    print("")
    print("--- Act 4: Good prompt + good artifact ---")
    run(
        [
            sys.executable,
            "-m",
            "prompt_failure_analyzer",
            "analyze",
            "--prompt",
            "demo/prompts/good_prompt.txt",
            "--output",
            "markdown",
        ]
    )
    run(
        [
            sys.executable,
            "-m",
            "release_governor",
            "evaluate",
            "--locc-artifact",
            "demo/fixtures/locc_good.json",
            "--env",
            "staging",
            "--sha",
            "deadbeef",
            "--audit-log",
            AUDIT_LOG,
        ]
    )

    print("")
    print("=== Demo complete. ===")


if __name__ == "__main__":
    main()
