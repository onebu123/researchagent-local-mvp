# ResearchAgent Developer Agent Guide

This repository is an auditable all-in-one research agent workspace. It is not a paper-writing service, not a citation forgery tool, and not a shortcut around real experiments, statistical review, human citation checks, peer review, or publication decisions.

## Project Mission

ResearchAgent helps a local workspace move from literature ingestion, knowledge indexing, data analysis, evidence-grounded drafting, claim verification, reviewer simulation, revision planning, human approval, and exportable audit packages while preserving provenance and explicit limitations.

## Research Integrity Rules

- Do not fabricate DOI values, authors, years, journals, pages, p-values, statistical significance, causal conclusions, experimental results, verified references, benchmark results, or user counts.
- Do not claim production readiness, compliance readiness, peer review readiness, or publication acceptance.
- `LLM_MODE` defaults to `mock`. Live LLM mode is optional and must not be required by tests.
- Tests and demo validation must not depend on real API keys, external networks, or external research services.
- Mock/demo output must be visibly labeled as mock/demo and must not be presented as real scientific evidence.
- Every output that touches claims, citations, reviewers, revisions, or exports must preserve evidence, provenance, and audit context.
- Use project-relative paths in generated artifacts and documentation examples. Do not expose local absolute paths, secrets, API keys, or stack traces.
- Keep changes small and reviewable. Split large refactors into small pull requests.

## Repo Layout

```text
services/api/       FastAPI backend, tools, workflows, API routers, tests
apps/web/           Next.js command center UI, components, Playwright tests
scripts/            Demo, validation, release packaging, evidence collection, verification
docs/               Current docs plus archived historical acceptance reports
.github/            CI, issue templates, pull request template
projects/           Runtime workspace, ignored by git
dist/               Release output, ignored by git
reports/            Local verification reports, ignored by git
```

## Backend Conventions

- Keep backend code offline-first and deterministic in mock mode.
- Register new behavior through small tools, explicit workflow functions, and API routes with tests.
- Do not hard-code `LLMClient(mode="mock")` inside feature code. Use the configured global client or dependency injection so live mode remains optional.
- Store artifacts under the project workspace with relative paths in JSON, manifests, logs, and exports.
- Never mark unverified metadata, demo passages, or fallback parser output as human verified.
- Reviewer, safety, RAG, revision, export, and packaging changes need focused regression tests.

## Frontend Conventions

- The homepage is the ResearchAgent Command Center: Project Setup, Knowledge & Evidence Index, Research & Analysis, Manuscript & Review Loop, and Export & Trust Report.
- Keep `apps/web/app/page.tsx` thin. Put workspace logic under `apps/web/features/workspace/`.
- Keep `apps/web/lib/api.ts` as a compatibility re-export if the API client is split.
- Preserve mock fallback UI when the backend is unavailable, and label it as Demo Mode or Mock Mode.
- Do not add `dangerouslySetInnerHTML` or new `localStorage` state without a specific reviewed reason.
- Do not introduce new UI libraries for small layout work.

## Testing Commands

Run the narrow test for your change first, then broader checks when touching shared behavior:

```bash
python -m compileall services/api scripts
python -m pytest services/api/tests -q
python scripts/run_demo.py
python scripts/validate_v2.py
python scripts/verify_local.py
cd apps/web && npm run typecheck
cd apps/web && npm run build
cd apps/web && npx playwright test
```

CI runs local-first checks with `LLM_MODE=mock`.

## Release Packaging Rules

- Use `python scripts/package_release.py --version v3.0.0-rc1 --output-dir dist`.
- Zip entries must use POSIX `/` paths.
- Source packages must exclude `.git`, `node_modules`, `.next`, `.pytest_cache`, `__pycache__`, `*.pyc`, `projects/*`, `dist/*`, `reports/*`, test reports, Playwright reports, and `.env*`.
- `.env.example` is allowed and must not contain real secrets.
- Evidence packages must record command results without secrets or local absolute paths.
- Failed tests or dirty git status must be reported as failures, not release-ready evidence.

## What Not To Do

- Do not delete historical acceptance reports. Link them from docs/archive or an archive index.
- Do not fabricate research metadata, statistical evidence, experimental conclusions, benchmarks, users, or verified references.
- Do not add real API keys, passwords, tokens, private keys, or full local paths.
- Do not bypass manuscript safety, citation grounding, patch safety, or human approval gates.
- Do not make one large refactor when small pull requests can isolate the risk.

## Codex Task Checklist

1. Read the relevant files before editing.
2. Search callers and consumers before changing contracts.
3. Make the smallest coherent change.
4. Add or update focused tests when behavior changes.
5. Run the requested verification commands, or clearly state why a command could not run.
6. Report changed files, why they changed, commands run, and remaining risks.

Historical v0.x/v1.x constraints are preserved in [docs/archive/legacy_agent_constraints.md](docs/archive/legacy_agent_constraints.md).
