$ErrorActionPreference = "Continue"

$AUDIT_LOG = "$env:TEMP\demo_audit.jsonl"

Write-Host "=== LLM Reliability Stack Demo ==="
Write-Host ""

Write-Host "--- Act 1: PFA analysis of bad prompt ---"
& pfa analyze --prompt demo/prompts/bad_prompt.txt --output markdown

Write-Host ""
Write-Host "--- Act 2: Release Governor gates bad artifact ---"
& release-governor evaluate `
  --locc-artifact demo/fixtures/locc_bad.json `
  --env staging `
  --sha deadbeef `
  --audit-log $AUDIT_LOG
$null

Write-Host ""
Write-Host "--- Audit log after block ---"
if (Test-Path $AUDIT_LOG) { Get-Content $AUDIT_LOG } else { "(audit log not found)" }

Write-Host ""
Write-Host "--- Act 3: Override path ---"
& release-governor evaluate `
  --locc-artifact demo/fixtures/locc_bad.json `
  --env staging `
  --sha deadbeef `
  --override-file demo/fixtures/override_demo.json `
  --audit-log $AUDIT_LOG

Write-Host ""
Write-Host "--- Audit log after override ---"
if (Test-Path $AUDIT_LOG) { Get-Content $AUDIT_LOG } else { "(audit log not found)" }

Write-Host ""
Write-Host "--- Act 4: Good prompt + good artifact ---"
& pfa analyze --prompt demo/prompts/good_prompt.txt --output markdown
& release-governor evaluate `
  --locc-artifact demo/fixtures/locc_good.json `
  --env staging `
  --sha deadbeef `
  --audit-log $AUDIT_LOG

Write-Host ""
Write-Host "=== Demo complete. ==="

