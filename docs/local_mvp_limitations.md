# Current Limitations

ResearchAgent is a local-first research agent workspace. It is designed for auditable project organization and demo validation, not as a replacement for real experiments, domain expertise, statistical review, citation verification, peer review, or publication decisions.

## Research Integrity Limits

- It does not fabricate DOI values, authors, years, journals, pages, p-values, statistical significance, causal conclusions, experimental results, or verified references.
- The Statistical Assistant is descriptive only: it does not generate p-values and does not perform causal inference.
- It does not turn placeholder metadata into verified references.
- It does not make demo data or mock output scientifically true.
- It does not guarantee publication, acceptance, compliance, or correctness.

## Runtime Limits

- `LLM_MODE=mock` is the default.
- Live LLM mode is optional and must be configured locally.
- Tests and demo validation must not require external networks, real API keys, or external research services.
- RAG retrieval is local/offline unless a future optional adapter is explicitly configured.

## Deployment Scaffold Limits

ResearchAgent v2.0 added a Research Workspace scaffold. In the current `v3.0.0-rc1` repository, optional PostgreSQL, Redis, auth, Docker, and worker settings are planning aids for local validation.

Defaults remain:

```bash
DATABASE_BACKEND=sqlite
QUEUE_MODE=inline
AUTH_MODE=disabled
LLM_MODE=mock
```

The scaffold does not prove hosted deployment, backups, observability, tenant isolation, TLS, authorization, compliance evidence, or recovery plans. See [docs/deployment_v2.md](deployment_v2.md) and run:

```bash
python scripts/validate_v2.py
```

## Export Limits

Source and evidence packages are audit handoff artifacts. They must exclude runtime projects, local databases, `.env*`, secrets, caches, Playwright reports, and local absolute paths. They are not compliance certificates or peer review evidence.
