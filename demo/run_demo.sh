#!/usr/bin/env bash
set -e

echo "=== LLM Reliability Stack Demo ==="
echo ""

echo "--- Act 1: PFA analysis of bad prompt ---"
pfa analyze --prompt demo/prompts/bad_prompt.txt --output markdown

echo ""
echo "--- Act 2: Release Governor gates bad artifact ---"
release-governor evaluate \
  --locc-artifact demo/fixtures/locc_bad.json \
  --env staging \
  --sha deadbeef \
  --audit-log /tmp/demo_audit.jsonl || true

echo ""
echo "--- Audit log after block ---"
cat /tmp/demo_audit.jsonl

echo ""
echo "--- Act 3: Override path ---"
release-governor evaluate \
  --locc-artifact demo/fixtures/locc_bad.json \
  --env staging \
  --sha deadbeef \
  --override-file demo/fixtures/override_demo.json \
  --audit-log /tmp/demo_audit.jsonl

echo ""
echo "--- Audit log after override ---"
cat /tmp/demo_audit.jsonl

echo ""
echo "--- Act 4: Good prompt + good artifact ---"
pfa analyze --prompt demo/prompts/good_prompt.txt --output markdown
release-governor evaluate \
  --locc-artifact demo/fixtures/locc_good.json \
  --env staging \
  --sha deadbeef \
  --audit-log /tmp/demo_audit.jsonl

echo ""
echo "=== Demo complete. ==="
