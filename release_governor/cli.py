import json
import sys

import click

from release_governor.engine.decision import make_decision
from release_governor.engine.leakage import primary_leakage_type
from release_governor.engine.loader import (
    compute_identity_hash,
    load_locc_artifact,
    load_override_file,
)
from release_governor.engine.override_manager import (
    create_override,
    expire_override,
    list_overrides,
    validate_override_file,
)
from release_governor.reporters.github_reporter import (
    load_pfa_summary,
    post_pr_comment,
    render_pr_comment,
)
from release_governor.reporters.json_reporter import render_json
from release_governor.reporters.markdown_reporter import render_markdown

_EXIT_CODES = {"ALLOW": 0, "BLOCK": 1, "REQUIRE_OVERRIDE": 2}


@click.group()
def cli():
    pass


@cli.command()
@click.option("--locc-artifact", required=True, type=click.Path(), help="Path to locc artifact JSON")
@click.option("--env", required=True, type=click.Choice(["staging", "preprod", "prod"]), help="Target environment")
@click.option("--sha", required=True, help="HEAD commit SHA")
@click.option("--override-file", default=None, type=click.Path(), help="Path to override file JSON")
@click.option("--output", default="json", type=click.Choice(["json", "markdown"]), help="Output format")
def run(locc_artifact, env, sha, override_file, output):
    try:
        artifact = load_locc_artifact(locc_artifact)
    except (ValueError, OSError) as e:
        click.echo(f"Error loading artifact: {e}")
        sys.exit(1)

    artifact_hash = compute_identity_hash(artifact)

    override = None
    if override_file is not None:
        try:
            override = load_override_file(override_file)
        except (ValueError, OSError) as e:
            click.echo(f"Error loading override: {e}")
            sys.exit(1)

    result = make_decision(artifact, env, sha, artifact_hash, override)

    if output == "json":
        click.echo(render_json(result, artifact_hash, env))
    else:
        click.echo(render_markdown(result, artifact_hash, env))

    sys.exit(_EXIT_CODES[result.decision])


@cli.command()
@click.option("--locc-artifact", required=True, type=click.Path(), help="Path to locc artifact JSON")
@click.option("--env", required=True, type=click.Choice(["staging", "preprod", "prod"]), help="Target environment")
@click.option("--sha", required=True, help="HEAD commit SHA")
@click.option("--override-file", default=None, type=click.Path(), help="Path to override file JSON")
@click.option("--audit-log", default=None, type=click.Path(), help="Append audit event to this .jsonl file")
@click.option("--pfa-findings", default=None, type=click.Path(), help="Path to pfa_findings.json emitted by PFA")
@click.option("--comment", is_flag=True, default=False, help="Post result as GitHub PR comment")
@click.option("--github-token", default=None, envvar="GITHUB_TOKEN", help="GitHub API token")
@click.option("--repo", default=None, envvar="GITHUB_REPOSITORY", help="GitHub repo (owner/name)")
@click.option("--pr-number", default=None, type=int, envvar="GITHUB_PR_NUMBER", help="PR number")
def evaluate(
    locc_artifact,
    env,
    sha,
    override_file,
    audit_log,
    pfa_findings,
    comment,
    github_token,
    repo,
    pr_number,
):
    try:
        artifact = load_locc_artifact(locc_artifact)
    except (ValueError, OSError) as e:
        click.echo(f"Error loading artifact: {e}")
        sys.exit(1)

    artifact_hash = compute_identity_hash(artifact)

    override = None
    if override_file is not None:
        try:
            override = load_override_file(override_file)
        except (ValueError, OSError) as e:
            click.echo(f"Error loading override: {e}")
            sys.exit(1)

    result = make_decision(
        artifact,
        env,
        sha,
        artifact_hash,
        override,
        override_file=override_file,
        audit_log_path=audit_log,
    )

    output_dict = {
        "decision": result.decision,
        "env": env,
        "artifact_hash": artifact_hash,
        "leakage": result.leakage,
        "override_failures": result.override_failures,
        "notes": result.notes,
    }
    json_output = json.dumps(output_dict, indent=2)

    with open("governor_decision.json", "w", encoding="utf-8") as f:
        f.write(json_output)

    click.echo(json_output)

    if comment:
        pfa_summary = load_pfa_summary(pfa_findings) if pfa_findings else None
        pr_comment_body = render_pr_comment(
            result,
            artifact_hash,
            env,
            "governor_decision.json",
            pfa_summary,
        )
        if pr_number is not None:
            post_pr_comment(pr_comment_body, repo, pr_number, github_token)
        else:
            encoded = (pr_comment_body + "\n").encode("utf-8")
            try:
                sys.stdout.buffer.write(encoded)
                sys.stdout.buffer.flush()
            except AttributeError:
                click.echo(pr_comment_body)

    exit_code = _EXIT_CODES[result.decision]
    if exit_code != 0:
        leakage_type = primary_leakage_type(result.leakage)
        click.echo(
            f"PROMOTION BLOCKED [{env}]: {leakage_type}. See governor_decision.json.",
            err=True,
        )

    sys.exit(exit_code)


@cli.group()
def override():
    pass


@override.command("create")
@click.option("--env", required=True, type=click.Choice(["staging", "preprod", "prod"]))
@click.option("--approved-by", required=True, type=str)
@click.option("--reason", required=True, type=str)
@click.option("--leakage-types", required=True, multiple=True, type=str)
@click.option("--sha", required=True, type=str)
@click.option("--identity-hash", required=True, type=str)
@click.option("--expires-in-days", default=7, type=int)
@click.option("--filename", default=None, type=str)
def override_create(env, approved_by, reason, leakage_types, sha, identity_hash, expires_in_days, filename):
    path = create_override(
        env=env,
        approved_by=approved_by,
        reason=reason,
        leakage_types=list(leakage_types),
        sha=sha,
        identity_hash=identity_hash,
        expires_in_days=expires_in_days,
        filename=filename,
    )
    errors = validate_override_file(str(path))
    if errors:
        for error in errors:
            click.echo(error, err=True)
        try:
            path.unlink()
        except OSError:
            pass
        sys.exit(1)

    payload = json.loads(path.read_text(encoding="utf-8"))
    click.echo(f"Override created: {path}")
    click.echo("Commit this file to enable override in CI.")
    click.echo(json.dumps(payload, indent=2))
    sys.exit(0)


@override.command("list")
@click.option("--env", default=None, type=str)
@click.option("--json", "json_mode", is_flag=True, default=False)
def override_list(env, json_mode):
    overrides = list_overrides(env=env)
    if not overrides:
        click.echo("No overrides found.")
        sys.exit(0)

    if json_mode:
        click.echo(json.dumps(overrides, indent=2))
        sys.exit(0)

    headers = ["PATH", "ENV", "APPROVED_BY", "LEAKAGE_TYPES", "EXPIRES_AT", "STATUS"]
    rows = []
    for item in overrides:
        status = item.get("_status", "invalid")
        if status == "expired":
            status = "[EXPIRED] expired"
        elif status == "invalid":
            status = "[INVALID] invalid"
        rows.append(
            [
                item.get("_path", ""),
                item.get("scope", ""),
                item.get("approved_by", ""),
                ",".join(item.get("leakage_types", [])) if isinstance(item.get("leakage_types"), list) else "",
                item.get("expires_at", ""),
                status,
            ]
        )

    widths = [len(h) for h in headers]
    for row in rows:
        for i, value in enumerate(row):
            widths[i] = max(widths[i], len(str(value)))

    header_line = " | ".join(headers[i].ljust(widths[i]) for i in range(len(headers)))
    click.echo(header_line)
    for row in rows:
        click.echo(" | ".join(str(row[i]).ljust(widths[i]) for i in range(len(row))))
    sys.exit(0)


@override.command("expire")
@click.option("--path", required=True, type=click.Path())
def override_expire(path):
    try:
        expire_override(path)
    except (OSError, json.JSONDecodeError, ValueError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    click.echo(f"Override expired: {path}")
    click.echo("Commit this change to remove override from CI.")
    sys.exit(0)


@override.command("validate")
@click.option("--path", required=True, type=click.Path())
def override_validate(path):
    errors = validate_override_file(path)
    if not errors:
        click.echo("Override file is valid.")
        sys.exit(0)
    for error in errors:
        click.echo(error, err=True)
    sys.exit(1)
