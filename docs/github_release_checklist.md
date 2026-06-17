# GitHub Release Checklist

Use this checklist before publishing `v3.0.0-rc1` source or evidence packages.

## Required Commands

- [ ] `python -m compileall services/api scripts`
- [ ] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest services/api/tests -q`
- [ ] `python scripts/evaluate_local_researchagent.py --output /tmp/researchagent_local_eval.json`
- [ ] `python scripts/check_secrets_static.py`
- [ ] `python scripts/validate_v38.py`
- [ ] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python scripts/run_auto_scientist_demo.py --project-id demo_auto_scientist_release --max-ideas 1 --max-experiments-per-idea 1 --generated-code --tree-search --output /tmp/researchagent_auto_scientist_demo.json`
- [ ] `python scripts/validate_v38.py --demo-report /tmp/researchagent_auto_scientist_demo.json --output /tmp/researchagent_validate_v38.json`
- [ ] `python scripts/package_release.py --version v3.0.0-rc1 --output-dir dist`
- [ ] `cd apps/web && npm ci && npm run typecheck && NEXT_TELEMETRY_DISABLED=1 npm run build`
- [ ] Optional: `cd apps/web && npx playwright install chromium && npx playwright test --project=chromium`

## Version Surfaces

- [ ] README current version is `v3.0.0-rc1`.
- [ ] `services/api/main.py` health/version reports `v3.0.0-rc1`.
- [ ] `services/api/pyproject.toml` uses `3.0.0rc1`.
- [ ] `apps/web/package.json` and `apps/web/package-lock.json` use `3.0.0-rc1`.
- [ ] UI workspace signals show `v3.0.0-rc1`.
- [ ] `scripts/package_release.py`, `scripts/collect_evidence.py`, and `scripts/verify_local.py` default to `v3.0.0-rc1`.
- [ ] `docs/release_v3.md` and `docs/roadmap.md` describe the release-candidate scope.

## Package Hygiene

- [ ] Source/evidence packages do not include `.git/`, `.env`, `.env.*`, `projects/`, `dist/`, `reports/`, `node_modules/`, `.next/`, caches, local databases, Playwright reports, or generated zips.
- [ ] `.env.example` is included and contains only local placeholder defaults.
- [ ] Zip entries use relative POSIX paths.
- [ ] Package scans do not find API keys, passwords, private keys, or local absolute paths.

## Integrity Notes

- [ ] Release notes do not claim production readiness, peer review, compliance certification, citation verification guarantee, publication acceptance, or scientific proof.
- [ ] Demo reports and generated papers remain explicitly local/demo artifacts requiring human review.
- [ ] Generated-code experiments remain sandboxed, reviewable, and/or approval-gated.
- [ ] Docker sandbox behavior is documented as optional and machine-dependent.
