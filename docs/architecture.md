# Architecture

## Design Principles
- Deterministic: no LLMs in the enforcement chain
- Layered: each tool catches what the prior layer cannot
- Auditable: every decision is logged with commit SHA and actor
- Local-first: no SaaS, no UI, no external dependencies beyond GitHub

## Data Flow

```text
bad_prompt.txt
    │
    ▼
[PFA] pfa analyze
    │ pfa_findings.json
    │ predicted locc failures: pii.direct_exposure, contract.pii_policy
    ▼
[locc] locc run
    │ locc_result.json (FAIL)
    │ checks: pii policy violated, schema missing field
    ▼
[Release Governor] release-governor evaluate
    │ governor_decision.json (BLOCK)
    │ leakage: pii=True, schema=True
    │ audit log: PROMOTION_BLOCKED, actor=system
    ▼
[EGA] per-request enforcement
    │ blocks non-conforming outputs at runtime
    ▼
Production (only conforming outputs reach here)
```

## Override Flow

```text
leakage detected
    │
    ▼
engineer runs: release-governor override create
    │
    ▼
override committed to overrides/{env}/
    │
    ▼
CI re-runs: override validated (SHA, expiry, leakage_types)
    │
    ▼
ALLOW with audit event OVERRIDE_USED
```

## Artifact Schema Reference

| Artifact | Produced by | Consumed by | Format |
|---|---|---|---|
| pfa_findings.json | PFA | RG PR comment | JSON |
| locc_result.json | locc | Release Governor | JSON |
| governor_decision.json | RG | CI / PR comment | JSON |
| rg_audit.jsonl | RG | humans / tooling | JSONL |
| overrides/{env}/*.json | engineer | RG override check | JSON |
