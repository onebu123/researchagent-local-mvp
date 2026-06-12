## Summary

- 

## Validation

- [ ] `python -m compileall services/api scripts`
- [ ] `python -m pytest services/api/tests -q`
- [ ] `python scripts/validate_v2.py`
- [ ] `cd apps/web && npm run typecheck`
- [ ] `cd apps/web && npm run build`
- [ ] `cd apps/web && npx playwright test`

## Research Integrity

- [ ] No fabricated DOI, metadata, p-values, significance, causal claims, or verified references.
- [ ] Mock/demo outputs remain labeled.
- [ ] No secrets, runtime artifacts, or local absolute paths added.
