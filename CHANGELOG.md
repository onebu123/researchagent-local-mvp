# Changelog

## v3.0.0-rc1

ResearchAgent is now packaged as an AI-Scientist-style local release candidate with a verifiable end-to-end demo and release-readiness contract.

Highlights:

- Adds an Auto Scientist workspace narrative around Ideas → Experiments → Code Review → Paper → Trust.
- Supports local idea generation, experiment plans, registered experiments, generated-code proposals, optional sandbox execution, reviewer-style code diagnostics, experiment tree search, selected-node reruns, paper rewriting, and best-node revision plans.
- Adds local background job records, logs, event timelines, SSE event streaming, cooperative cancellation, and trust-package capture for Auto Scientist jobs.
- Adds experiment-result to manuscript-claim binding and paper-level citation/source-passage binding.
- Adds LaTeX compile reporting with safe fallback PDF preview when a compiler is unavailable.
- Adds an end-to-end Auto Scientist demo script and `scripts/validate_v38.py` release-candidate validation contract.
- Aligns backend, frontend, package, docs, release scripts, and UI version surfaces to `v3.0.0-rc1`.
- Keeps `LLM_MODE=mock` as the default and continues to avoid required external API keys or external research services in tests and demos.

Integrity boundaries:

- Auto-generated ideas, experiments, drafts, citations, reviews, revisions, and trust packages require human review.
- Generated-code execution remains sandboxed, reviewable, and/or approval-gated by policy.
- Citation binding is not citation verification guarantee.
- Experiment tree scores are workflow heuristics, not scientific validity metrics.
- Evidence Trust Packages are audit handoff artifacts, not compliance certificates or publication-readiness certificates.

## Earlier Local MVP Milestones

Historical v0.x, v1.x, v2.0, and v2.x acceptance criteria/reports are preserved under `docs/` for auditability. Start with [docs/archive.md](docs/archive.md).
