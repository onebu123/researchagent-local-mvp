## Summary

-

## Scope

- [ ] Backend
- [ ] Frontend
- [ ] Docs / GitHub presentation
- [ ] Release packaging / evidence
- [ ] Tests only

## Validation

- [ ] `python -m compileall services/api scripts`
- [ ] `python -m pytest services/api/tests -q`
- [ ] `python scripts/validate_v2.py`
- [ ] `python scripts/verify_local.py`
- [ ] `cd apps/web && npm run typecheck`
- [ ] `cd apps/web && npm run build`
- [ ] `cd apps/web && npx playwright test`

If any command was skipped or failed, explain why:


## Research Integrity

- [ ] No fabricated DOI, authors, years, journals, pages, p-values, significance, causal claims, experimental conclusions, or verified references.
- [ ] No production-ready, compliance-ready, peer-review-ready, benchmark, user-count, or publication-acceptance claims.
- [ ] Mock/demo outputs remain labeled.
- [ ] Evidence, provenance, audit logs, and human approval context are preserved.
- [ ] No secrets, runtime artifacts, or local absolute paths added.

## Notes For Reviewers

-
