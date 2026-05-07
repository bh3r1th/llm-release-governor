# Changelog

## v0.1.0

Initial release.

Features:
- Promotion gate: ALLOW / BLOCK / REQUIRE_OVERRIDE
- Three leakage classifiers: PII, schema, policy — reported separately
- Multi-leakage override: all detected types must be covered, partial blocks
- SHA-bound overrides: wildcard rejected, rotation enforced
- Override audit log (JSONL) on every decision
- Override management CLI: create / list / expire / validate
- GitHub Actions integration
- PR comment: leakage report + override status
