# GitHub Release Checklist

Use this checklist before publishing a `v2.0.1-dev` source or evidence package.

## Local Validation

- [ ] `python -m compileall services/api scripts`
- [ ] `python -m pytest services/api/tests -q`
- [ ] `python scripts/run_demo.py`
- [ ] `python scripts/validate_v2.py`
- [ ] `cd apps/web && npm run typecheck`
- [ ] `cd apps/web && npm run build`
- [ ] `cd apps/web && npx playwright test`
- [ ] `python scripts/check_secrets_static.py`

## Release Packaging

- [ ] `python scripts/package_release.py --version v2.0.1-dev --output-dir dist`
- [ ] Source zip entries use POSIX `/` paths.
- [ ] Source zip excludes `.git`, `node_modules`, `.next`, `.pytest_cache`, `__pycache__`, `*.pyc`, `projects/*`, `dist/*`, test reports, Playwright reports, and `.env*`.
- [ ] `.env.example` is included and contains placeholders only.
- [ ] Evidence package records command results without secrets or local absolute paths.
- [ ] Failed tests or dirty git status are not described as release-ready.

## Git Hygiene

- [ ] `git status --short` is reviewed.
- [ ] Runtime artifacts are ignored rather than staged.
- [ ] Historical acceptance reports remain in `docs/` or the archive index.

## Version Surfaces

- [ ] README current version is `v2.0.1-dev`.
- [ ] `services/api/pyproject.toml` uses `2.0.1.dev0`.
- [ ] `apps/web/package.json` uses `2.0.1-dev`.
- [ ] FastAPI health/version reports `v2.0.1-dev`.
