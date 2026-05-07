import sys

import click

from prompt_failure_analyzer.engine.analyzers.constraint_risk import analyze_constraint_risk
from prompt_failure_analyzer.engine.analyzers.pii_risk import analyze_pii_risk
from prompt_failure_analyzer.engine.analyzers.schema_risk import analyze_schema_risk
from prompt_failure_analyzer.engine.loader import load_prompt
from prompt_failure_analyzer.engine.reporter import build_summary, render_json, render_markdown


@click.group()
def cli():
    pass


@cli.command("analyze")
@click.option("--prompt", required=True, type=click.Path(exists=True))
@click.option("--output", default="json", type=click.Choice(["json", "markdown"]))
@click.option("--out-file", default=None, type=click.Path())
def analyze(prompt, output, out_file):
    prompt_data = load_prompt(prompt)
    findings = []
    findings.extend(analyze_schema_risk(prompt_data))
    findings.extend(analyze_pii_risk(prompt_data))
    findings.extend(analyze_constraint_risk(prompt_data))

    summary = build_summary(findings)
    rendered = (
        render_json(findings, summary, prompt)
        if output == "json"
        else render_markdown(findings, summary, prompt)
    )

    if out_file:
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(rendered)

    try:
        sys.stdout.buffer.write((rendered + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()
    except AttributeError:
        click.echo(rendered)
    sys.exit(0 if summary["passed"] else 1)


if __name__ == "__main__":
    cli()
