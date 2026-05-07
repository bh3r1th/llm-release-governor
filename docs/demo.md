# 3-Minute Demo Script

## Setup (30s)
```bash
pip install -e ".[dev]"
ls demo/
```

## Act 1 — Bad prompt (60s)
```bash
pfa analyze --prompt demo/prompts/bad_prompt.txt --output markdown
```
Expected highlights:
- `PII_FIELD_REQUESTED` (HIGH)
- `AMBIGUOUS_CONSTRAINT` (HIGH)
- predicted locc failures listed

## Act 2 — CI gate (60s)
```bash
release-governor evaluate \
  --locc-artifact demo/fixtures/locc_bad.json \
  --env staging \
  --sha deadbeef \
  --audit-log /tmp/demo_audit.jsonl
```
Expected: BLOCK, exit 1

```bash
cat /tmp/demo_audit.jsonl
```
Expected: `PROMOTION_BLOCKED`

## Act 3 — Override + re-gate (30s)
```bash
release-governor evaluate \
  --locc-artifact demo/fixtures/locc_bad.json \
  --env staging \
  --sha deadbeef \
  --override-file demo/fixtures/override_demo.json \
  --audit-log /tmp/demo_audit.jsonl
```
Expected: ALLOW, exit 0

```bash
cat /tmp/demo_audit.jsonl
```
Expected additional event: `OVERRIDE_USED`

## Act 4 — Good prompt (30s)
```bash
pfa analyze --prompt demo/prompts/good_prompt.txt --output markdown
```
Expected: 0 findings, ✅

```bash
release-governor evaluate \
  --locc-artifact demo/fixtures/locc_good.json \
  --env staging \
  --sha deadbeef
```
Expected: ALLOW, exit 0

## What you just saw
- bad prompt → PFA predicted failure → RG blocked promotion
- override path → auditable, SHA-bound, expirable
- good prompt → clean through the full stack
