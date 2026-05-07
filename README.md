# LLM Reliability Stack

LLM outputs are non-deterministic, and failures often surface only after deployment unless reliability checks are layered through the lifecycle. Without design-time and promotion-time enforcement, schema drift, PII leakage, and hard-constraint violations can move silently from prompt authoring to production. This repository demonstrates a production-grade stack that catches those classes of failures before runtime and records auditable decisions at each gate.

## The Stack

```text
┌─────────────────────────────────────────────────────────┐
│                   LLM Reliability Stack                  │
├──────────────┬──────────────┬──────────────┬────────────┤
│  Design-time │      CI      │   Staging    │  Runtime   │
│     PFA      │     locc     │   Release    │    EGA     │
│              │              │   Governor   │            │
├──────────────┼──────────────┼──────────────┼────────────┤
│ Static prompt│ Schema +     │ Leakage +    │ Per-request│
│ analysis     │ contract     │ promotion    │ output     │
│              │ check        │ gate         │ enforcement│
└──────────────┴──────────────┴──────────────┴────────────┘
```

## What Each Layer Does

### PFA (design-time)
PFA statically analyzes prompt templates before CI. It flags structural patterns likely to cause downstream failures in schema, PII, and constraint classes, and maps those findings to predicted locc failure codes. It emits JSON and Markdown reports for prompt authors and reviewers. It does not execute prompts and does not call an LLM.

### locc (CI)
locc validates contract behavior on CI artifacts and classifies outcomes as PASS, HOLD, or FAIL with named checks/failure signals. It verifies schema compatibility and policy conformance on the generated artifact boundary used by promotion gates. It produces `locc_result.json` for downstream consumers. It does not make promotion decisions.

### Release Governor (staging)
Release Governor evaluates locc artifacts against leakage detectors and override policy before promotion. It emits `governor_decision.json`, optional PR comments, and optional JSONL audit events. It enforces SHA-bound, expirable, scope-bound overrides with full leakage-type coverage. It does not execute runtime traffic.

### EGA (runtime)
EGA enforces response-time reliability rules for live requests. It blocks or remediates outputs that violate runtime constraints and policy. It is the last line of defense when traffic patterns differ from CI fixtures. It does not replace pre-deployment gates.

## The Canonical Flow

1. Analyze prompt risk before CI.
   ```bash
   pfa analyze --prompt demo/prompts/bad_prompt.txt --output json
   ```
   Snippet:
   ```json
   {"summary":{"high":4},"findings":[{"pattern":"PII_FIELD_REQUESTED"}]}
   ```

2. Run contract checks in CI.
   ```bash
   locc run --contract contracts/current.json --snapshot snapshots/current.json
   ```
   Snippet (`demo/fixtures/locc_bad.json` equivalent):
   ```json
   {"status":"FAIL","checks":[{"name":"pii_policy","result":"FAIL"}]}
   ```

3. Gate promotion in staging.
   ```bash
   release-governor evaluate \
     --locc-artifact demo/fixtures/locc_bad.json \
     --env staging \
     --sha deadbeef
   ```
   Snippet:
   ```json
   {"decision":"BLOCK","leakage":{"pii":true,"schema":true}}
   ```

4. Optional override path (auditable, SHA-bound).
   ```bash
   release-governor evaluate \
     --locc-artifact demo/fixtures/locc_bad.json \
     --env staging \
     --sha deadbeef \
     --override-file demo/fixtures/override_demo.json
   ```
   Snippet:
   ```json
   {"decision":"ALLOW"}
   ```

5. Runtime enforcement remains active in EGA.

## Quickstart

```bash
pip install -e ".[dev]"

# Analyze a prompt
pfa analyze --prompt demo/prompts/bad_prompt.txt

# Run locc (assumes locc installed)
locc run --contract contracts/current.json --snapshot snapshots/current.json

# Gate promotion
release-governor evaluate \
  --locc-artifact locc_result.json \
  --env staging \
  --sha $GIT_SHA
```

## Versions

| Product          | Version |
|------------------|---------|
| PFA              | 0.1.0   |
| locc             | 1.1.0   |
| Release Governor | 0.1.0   |
| EGA              | 4       |

## Test Coverage

120 tests.

```bash
pytest tests/ -q
```
