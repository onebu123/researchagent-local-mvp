# Contributing

Thanks for helping improve ResearchAgent. Keep changes small, auditable, and aligned with the repository mission: an offline-first, evidence-preserving all-in-one research agent workspace.

Read [AGENTS.md](AGENTS.md) before making code changes.

## Local Setup

Backend:

```bash
cd services/api
python -m pip install -e .
```

Frontend:

```bash
cd apps/web
npm install
```

Default local environment:

```bash
APP_ENV=local
DATABASE_BACKEND=sqlite
QUEUE_MODE=inline
AUTH_MODE=disabled
LLM_MODE=mock
LLM_API_KEY=
```

## Validation

Run the narrow test for your change first. For shared behavior, run:

```bash
python -m compileall services/api scripts
python -m pytest services/api/tests -q
python scripts/run_demo.py
python scripts/validate_v2.py
python scripts/verify_local.py
cd apps/web && npm run typecheck
cd apps/web && npm run build
python scripts/check_secrets_static.py
```

Playwright is required when the UI workflow changes:

```bash
cd apps/web && npx playwright test
```

For release packaging:

```bash
python scripts/package_release.py --version v3.0.0-rc1 --output-dir dist
```

## Pull Request Expectations

- Explain what changed and why.
- Include the commands you ran and whether they passed.
- Keep mock/demo output visibly labeled.
- Preserve evidence, provenance, audit logs, and human approval context.
- Do not add real secrets, credentials, or absolute local paths.
- Do not remove historical acceptance reports.
- Avoid broad refactors unless the issue requires them.

## Research Integrity

Do not fabricate DOI values, authors, years, journals, pages, p-values, statistical significance, causal conclusions, experimental results, verified references, benchmark results, user counts, production readiness, or peer review readiness.
