# Contributing

Thanks for helping improve ResearchAgent. Keep changes small, auditable, and aligned with the repository mission: an offline-first, evidence-preserving research agent workspace.

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

Default environment:

```bash
LLM_MODE=mock
DATABASE_BACKEND=sqlite
QUEUE_MODE=inline
AUTH_MODE=disabled
```

## Validation

Run the same checks used by CI when your change touches shared behavior:

```bash
python -m compileall services/api scripts
python -m pytest services/api/tests -q
python scripts/validate_v2.py
cd apps/web && npm run typecheck
cd apps/web && npm run build
cd apps/web && npx playwright test
python scripts/check_secrets_static.py
```

For release packaging:

```bash
python scripts/package_release.py --version v2.0.1-dev --output-dir dist
```

## Pull Request Expectations

- Explain what changed and why.
- Include the commands you ran and their result.
- Keep mock/demo outputs labeled.
- Do not add real secrets or absolute local paths.
- Do not make large unrelated refactors.
- Do not remove historical acceptance reports.
- Link to [AGENTS.md](AGENTS.md) for coding-agent maintenance rules.

## Research Integrity

Do not fabricate DOI values, authors, years, journals, pages, p-values, statistical significance, causal conclusions, experimental results, or verified references. Live LLM mode is optional and must not be required by tests.
