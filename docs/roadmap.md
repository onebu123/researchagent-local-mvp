# Roadmap

This roadmap is intentionally conservative. ResearchAgent should become more useful without pretending to be a production service, peer review system, compliance product, publication engine, or scientific truth oracle.

## v3.0.0-rc1 AI-Scientist-style Release Candidate

Goals:

- Freeze the current AI-Scientist-style local workflow into a verifiable release candidate.
- Align backend, frontend, docs, package metadata, release scripts, and validation scripts on `v3.0.0-rc1`.
- Make the end-to-end local demo the primary release-readiness contract.
- Preserve mock/offline defaults, generated-code safety gates, human approval requirements, and audit-package exports.

Deliverables:

- Auto Scientist Workbench with Ideas, Experiments, Code Review, Paper, and Trust workflow areas.
- Background job records, event timelines, SSE event stream, and cooperative cancellation.
- Generated-code proposal lifecycle with static scan, source hash, optional approval gate, sandbox execution, and rerun record.
- Experiment tree search, selected-node reruns, selected-node paper rewrites, and best-node revision planning.
- Experiment-claim binding, paper-citation binding, LaTeX compile report, fallback preview PDF, and Evidence Trust Package export.
- `scripts/run_auto_scientist_demo.py` end-to-end local demo.
- `scripts/validate_v38.py` release-candidate validation contract.
- CI matrix coverage for backend, frontend, static security, release readiness, packaging, and demo validation.

Acceptance criteria:

- `python -m compileall services/api scripts` passes.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest services/api/tests -q` passes.
- `python scripts/validate_v38.py` passes.
- `python scripts/run_auto_scientist_demo.py ...` produces a report with all required local artifacts.
- `python scripts/validate_v38.py --demo-report <report>` passes.
- `python scripts/package_release.py --version v3.0.0-rc1 --output-dir <tmp>` passes.
- `cd apps/web && npm ci && npm run typecheck && NEXT_TELEMETRY_DISABLED=1 npm run build` passes.

Non-goals:

- Hosted production service claim.
- Formal peer review, citation verification guarantee, statistical validity guarantee, compliance certificate, or publication-readiness certificate.
- External benchmark claims.
- Unchecked arbitrary code execution.

## v3.0 Final Hardening

Goals:

- Stabilize the release candidate based on CI, local demo, and user feedback.
- Reduce long-running test flakiness and make E2E browser checks repeatable.
- Improve UI affordances for generated-code approval, experiment-tree node selection, patch approval, and trust-package download.

Deliverables:

- Release notes and migration notes from v2.x/v3.0.0-rc1.
- Expanded local eval fixtures for RAG, claim audit, citation binding, and Auto Scientist safety behavior.
- Optional Docker sandbox smoke test documentation for machines with local approved images.
- More explicit frontend error states, empty states, and job progress states.

Acceptance criteria:

- CI runs consistently within target time.
- End-to-end demo report remains stable.
- Trust package manifest includes all Auto Scientist job, code, experiment tree, claim binding, citation binding, compile, review, and revision artifacts.
- Demo and documentation keep limitations visible.

Non-goals:

- Real scientific discovery certification.
- Hosted multi-tenant deployment.
- Automatic paper submission.

## Future v3.x Directions

Potential future work after v3.0 final:

- Stronger local sandboxing and optional Docker/GPU runner management.
- Larger local evaluation suites and regression thresholds.
- More robust PDF parsing, OCR integration, and source locator quality reporting.
- Better generated-code repair loops with stricter approval gates.
- Full UI workflows for trust-package review, patch application, and paper version comparison.
- Optional live LLM synthesis as a strictly grounded layer, never as a source of evidence.
