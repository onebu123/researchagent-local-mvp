# Roadmap

The roadmap is intentionally conservative. ResearchAgent should become more useful without pretending to be a production service, peer review system, compliance product, or scientific truth oracle.

## v2.0.1 Quality Fix Release

Goals:
- Make repository presentation consistent and trustworthy.
- Keep all version surfaces aligned on `v2.0.1-dev`.
- Make release source and evidence packages reproducible.
- Keep CI local-first and mock-by-default.

Deliverables:
- Clean README, docs index, architecture docs, and product vision.
- Source/evidence packaging scripts with runtime artifact exclusions.
- Static secret scanning.
- GitHub Actions CI for backend, frontend, and static validation.
- Command Center homepage split from legacy panels.

Acceptance criteria:
- `python -m pytest services/api/tests -q` passes locally.
- `python scripts/validate_v2.py` passes locally.
- `cd apps/web && npm run typecheck && npm run build` passes locally.
- Release zips exclude projects, caches, `.env*`, test reports, and local absolute paths.

Non-goals:
- No production hosting claim.
- No real citation verification guarantee.
- No mandatory live LLM integration.

## v2.1 Research Agent Loop

Goals:
- Add a deterministic Generator -> Reviewer -> Reviser loop.
- Preserve round-by-round audit records.
- Keep human approval required for patches and final decisions.

Deliverables:
- Draft round artifacts.
- Reviewer round JSONL records.
- Revision plan artifacts.
- API and UI panels for iterative loop status.

Acceptance criteria:
- Mock loop is deterministic.
- Reviewer issues flow into revision plans.
- Revisions do not overwrite the official draft automatically.
- Run history and audit log are written for each round.

Non-goals:
- No automatic paper submission.
- No claim that reviewer simulation equals peer review.

## v2.2 Real Literature RAG

Goals:
- Upgrade local retrieval quality while staying offline-first.
- Add clearer parser quality and unsupported answer detection.

Deliverables:
- Hybrid keyword/BM25 or SQLite FTS retrieval.
- Optional local embedding adapter.
- Chunk quality and metadata trust scores.
- Source passage citation in answers.
- Manual eval set format and docs.

Acceptance criteria:
- RAG answers cite retrieved source passages.
- Unsupported questions return explicit unsupported notes.
- Low-quality parser fallback is not marked as verified evidence.

Non-goals:
- No external embedding API dependency.
- No online DOI lookup requirement.

## v2.3 Evaluation Benchmarks

Goals:
- Add repeatable local evaluation sets and regression reports.
- Make retrieval/drafting/audit changes easier to review.

Deliverables:
- Manual evaluation examples.
- Local benchmark runner.
- Versioned reports for retrieval and unsupported-answer behavior.

Acceptance criteria:
- Evaluation can run offline.
- Reports distinguish demo fixtures from real datasets.
- Metrics are not presented as external benchmark results.

Non-goals:
- No fabricated leaderboard claims.
- No claim of general scientific correctness.

## v3.0 All-in-one Research Agent Workspace

Goals:
- Integrate the command center, agent orchestration, RAG, analysis, manuscript loop, review, revision, and export workflows.
- Provide a coherent research audit package for handoff and review.

Deliverables:
- Stable agent contracts.
- Stronger tool registry.
- Richer trust dashboard.
- Exportable audit package with source, evidence, and review provenance.

Acceptance criteria:
- End-to-end local workflow is runnable without external services.
- Every generated claim has source/evidence status or is marked unsupported.
- Export packages are sanitized and reproducible.

Non-goals:
- No production-ready, compliance-ready, or peer-review-ready claim.
- No replacement for human research judgment.
