# Sample PR Walkthrough

## Scenario
An engineer adds a new customer-support prompt that asks for user email and phone number, then opens a PR against `main` targeting `staging`.

## Step 1 — PFA runs (design-time, pre-CI)
Command:
```bash
pfa analyze --prompt demo/prompts/bad_prompt.txt --output json
```
Representative output:
```json
{
  "summary": {"total": 7, "high": 4, "medium": 2, "low": 1, "passed": false},
  "findings": [
    {"analyzer": "pii_risk", "pattern": "PII_FIELD_REQUESTED", "predicted_locc_failures": ["pii.direct_exposure", "contract.pii_policy"]},
    {"analyzer": "constraint_risk", "pattern": "AMBIGUOUS_CONSTRAINT", "predicted_locc_failures": ["contract.hard_constraint_violated"]},
    {"analyzer": "schema_risk", "pattern": "UNTYPED_OUTPUT", "predicted_locc_failures": ["schema.type_mismatch", "schema.missing_field"]}
  ]
}
```
Annotations:
- `PII_FIELD_REQUESTED`: prompt explicitly asks for sensitive fields.
- `AMBIGUOUS_CONSTRAINT`: hard rule softened by hedge.
- `UNTYPED_OUTPUT`: output requested without explicit schema.

## Step 2 — locc runs (CI)
Artifact: `demo/fixtures/locc_bad.json`

```json
{
  "status": "FAIL",
  "checks": [
    {"name": "pii_policy", "result": "FAIL", "reasons": ["email address in output"]},
    {"name": "schema_contract", "result": "FAIL", "reasons": ["required field missing"]}
  ]
}
```
Mapping back to PFA:
- `pii_policy` ⚠️ predicted by PFA
- `required field missing` ⚠️ predicted by PFA
- Any unmodeled failure would be marked 🆕 not predicted by PFA

## Step 3 — Release Governor runs (staging gate)
```bash
release-governor evaluate --locc-artifact demo/fixtures/locc_bad.json --env staging --sha deadbeef
```
`governor_decision.json`:
```json
{"decision":"BLOCK","leakage":{"pii":true,"schema":true,"policy":true,"any":true}}
```
stderr:
```text
PROMOTION BLOCKED [staging]: pii. See governor_decision.json.
```
audit entry:
```json
{"event_type":"PROMOTION_BLOCKED","actor":"system"}
```

## Step 4 — Engineer creates override (optional path)
```bash
release-governor override create \
  --env staging \
  --approved-by demo-engineer \
  --reason "demo walkthrough — not for production use" \
  --leakage-types pii --leakage-types schema \
  --sha deadbeef \
  --identity-hash <artifact-hash>
```
Validation output confirms file creation and commit instruction.

## Step 5 — CI re-runs with override
`governor_decision.json` becomes:
```json
{"decision":"ALLOW"}
```
audit entry:
```json
{"event_type":"OVERRIDE_USED","actor":"demo-engineer"}
```

## Step 6 — PR comment (what the reviewer sees)
Rendered comment includes:
- `### PFA Pre-flight`
- Leakage matrix (PII/Schema/Policy)
- Override failure/status context
- Artifact path (`governor_decision.json`)
