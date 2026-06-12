# User Guide

This guide describes the current `v2.0.1-dev` local ResearchAgent workspace.

## First Screen

The homepage opens as the ResearchAgent Command Center. The primary workflow is:

1. Project Setup
2. Knowledge & Evidence Index
3. Research & Analysis
4. Manuscript & Review Loop
5. Export & Trust Report

The previous detailed panels are still available under Advanced / Diagnostics. They remain useful for inspecting evidence, provenance, review issues, audit logs, export state, and the Research Workspace scaffold.

## Recommended Local Flow

```bash
python scripts/reset_demo.py --yes
python scripts/seed_demo.py
python scripts/run_demo.py
```

Then start the backend and frontend:

```bash
cd services/api
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

```bash
cd apps/web
npm run dev -- --hostname 127.0.0.1 --port 3100
```

Open `http://127.0.0.1:3100`.

## What To Review

- Project health and uploaded artifacts.
- Literature index, RAG chunks, source passages, parser quality, and metadata status.
- Analysis provenance, descriptive statistics helpers, and figure provenance.
- Manuscript draft state, claim alignment, citation grounding, reviewer issues, and revision plans.
- Export package state, audit logs, trust dashboard, and release readiness checks.

## Mock Fallback

The web app preserves mock fallback when the backend is unavailable. Mock data must be treated as Demo Mode / Mock Mode output, not as a real research conclusion.

## Research Workspace Scaffold

ResearchAgent v2.0 introduced a Research Workspace scaffold for optional PostgreSQL, worker, auth, Docker, and deployment planning. Current `v2.0.1-dev` keeps those defaults local:

```bash
QUEUE_MODE=inline
AUTH_MODE=disabled
LLM_MODE=mock
```

See [docs/deployment_v2.md](deployment_v2.md). Validate the scaffold with:

```bash
python scripts/validate_v16.py
python scripts/validate_v2.py
```

## Release Packaging

```bash
python scripts/package_release.py --version v2.0.1-dev --output-dir dist
```

Review the generated source and evidence zips before publishing. They should exclude runtime projects, caches, `.env*`, local databases, and test reports.
