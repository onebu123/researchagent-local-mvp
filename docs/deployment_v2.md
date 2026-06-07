# ResearchAgent v2.0 Deployment Scaffold

This document describes the v2.0 Research Workspace scaffold. It is a local validation and operator planning guide, not a public deployment certificate.

## Default Local Mode

The default mode keeps the demo self-contained:

- `DATABASE_BACKEND=sqlite`
- `QUEUE_MODE=inline`
- `AUTH_MODE=disabled`
- `LLM_MODE=mock`
- `python scripts/validate_v2.py`

No API key, external network, PostgreSQL, Redis, auth secret, or cloud server is required for local validation.

## Optional PostgreSQL

PostgreSQL is scaffolded through Docker Compose profiles and environment variables:

```bash
set POSTGRES_PASSWORD=replace-with-local-dev-password
docker compose --profile postgres up postgres
```

Application use of PostgreSQL is optional and must be explicitly configured:

```bash
DATABASE_BACKEND=postgresql
DATABASE_URL=postgresql://research_agent:<password>@postgres:5432/research_agent
```

Do not commit `DATABASE_URL` or passwords. v2.0 does not automatically run external database migrations.

## Optional Queue And Worker

The default queue mode is inline. The worker scaffold can be smoke-tested without Redis:

```bash
python -m app.workers.research_worker
```

Optional queue infrastructure can be started locally:

```bash
docker compose --profile queue up redis
docker compose --profile worker up worker
```

External queue mode is a scaffold until worker locking, retries, idempotency, observability, and operator runbooks are reviewed.

## Optional Auth Scaffold

Auth is disabled by default for local demo use:

```bash
AUTH_MODE=disabled
```

Any shared environment must enforce auth server-side before exposure. Frontend controls are not a security boundary. Do not commit `AUTH_SHARED_SECRET` or token material.

## Frontend Origin And CORS

Local defaults allow only common localhost origins. If the web server runs on another port, set an explicit comma-separated allowlist:

```bash
CORS_ALLOW_ORIGINS=http://localhost:3100,http://127.0.0.1:3100
```

Do not use wildcard origins with credentials. Review CORS together with auth, cookies, CSRF, TLS, and reverse proxy headers before any shared deployment.

## Docker Compose

Default local containers:

```bash
docker compose up --build api web
```

Optional profiles:

```bash
docker compose --profile postgres --profile queue --profile worker up --build
```

Before any shared deployment, review TLS, CORS origins, secrets, backup and restore, monitoring, rollback, queue replay behavior, and auth enforcement.

## Required Guardrails

- Keep mock fallback available for demos.
- Keep secrets out of git, logs, reports, screenshots, and exports.
- Do not present scaffold status as peer review, compliance, or public production readiness.
- Do not fabricate DOI, citations, p-values, significance, causal claims, OCR output, or scientific conclusions.
