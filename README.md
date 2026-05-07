# Release Governor

**Block promotion when malformed LLM outputs leak past staging validation boundaries.**

Designed for staging/pre-prod environments with structured CI/CD workflows.

## Install

```bash
pip install llm-release-governor
```

## What it does

Release Governor sits between your CI contract checker and your staging
environment. It consumes a locc artifact, detects leakage the contract
checker allowed through, and enforces a promotion policy per environment.

locc (CI) -> Release Governor (staging gate) -> EGA (runtime)

## Quickstart

```bash
release-governor evaluate \
  --locc-artifact locc_result.json \
  --env staging \
  --sha $GIT_SHA
```

Exit 0 = ALLOW, Exit 1 = BLOCK, Exit 2 = REQUIRE_OVERRIDE

## What it detects

| Type | Signal |
|---|---|
| PII leakage | PII signals in locc check reasons |
| Schema leakage | Structural diffs locc allowed through |
| Policy leakage | Promotion violates env-specific rules |

## Override path

```bash
release-governor override create \
  --env staging \
  --approved-by alice \
  --reason "confirmed false positive" \
  --leakage-types pii \
  --sha $GIT_SHA \
  --identity-hash $ARTIFACT_HASH \
  --expires-in-days 7
```

Then: commit the override file and re-run evaluate.

## Audit log

```bash
release-governor evaluate \
  --locc-artifact locc_result.json \
  --env staging \
  --sha $GIT_SHA \
  --audit-log rg_audit.jsonl
```

```bash
{"event_type": "PROMOTION_BLOCKED", "sha": "...", "actor": "system"}
```

## GitHub Actions

```yaml
- name: Gate promotion
  run: |
    pip install locc llm-release-governor
    locc run --contract contracts/current.json \
             --snapshot snapshots/current.json \
             --output json > locc_result.json
    release-governor evaluate \
      --locc-artifact locc_result.json \
      --env staging \
      --sha ${{ github.sha }}
```

## Environment policies

| Environment | Policy |
|---|---|
| staging | FAIL blocks. HOLD allowed if no schema leakage |
| preprod | FAIL or HOLD blocks |
| prod | PASS only, no diffs, no leakage |

## Stack integration

Release Governor is part of the LLM Reliability Stack.

Consumes locc artifacts. Sits upstream of EGA.

| Layer | Tool |
|---|---|
| Design-time | PFA |
| CI | locc |
| Staging | **Release Governor** |
| Runtime | EGA |

## License

MIT

## Publishing

Releases are published automatically to PyPI on version tag push.

To release:

```bash
git tag v0.1.0
git push origin v0.1.0
```

To dry-run on TestPyPI first:

Trigger the "Publish to TestPyPI" workflow manually from GitHub Actions.

PyPI trusted publishing must be configured once per project:

PyPI project settings -> Publishing -> Add publisher
Owner: <org>
Repository: <repo>
Workflow: publish.yml
Environment: pypi
