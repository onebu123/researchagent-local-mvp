# ResearchAgent

[![CI](https://github.com/onebu123/researchagent-local-mvp/actions/workflows/ci.yml/badge.svg)](https://github.com/onebu123/researchagent-local-mvp/actions/workflows/ci.yml)
![Version](https://img.shields.io/badge/version-v3.0.0--rc1-blue)
![Default LLM mode](https://img.shields.io/badge/default%20LLM_MODE-mock-lightgrey)
![Research integrity](https://img.shields.io/badge/research%20integrity-human%20review%20required-green)

ResearchAgent is a local-first, auditable AI-Scientist-style workspace for moving from local evidence to generated research drafts, sandboxed experiment diagnostics, simulated review, human approval, and exportable trust packages.

It is not a scientific truth oracle, peer-review system, compliance product, or unchecked paper-writing service. Auto-generated ideas, experiments, code, drafts, citations, reviews, and revisions require human review. The system must not fabricate DOI values, authors, years, journals, pages, p-values, statistical significance, causal conclusions, experimental results, or verified references.

Current release candidate: `v3.0.0-rc1`.

Start here: [v3 release readiness](docs/release_v3.md) · [Auto Scientist MVP](docs/auto_scientist.md) · [Auto Scientist end-to-end demo](docs/auto_scientist_end_to_end_demo.md) · [Citation/compile pipeline](docs/citation_compile_pipeline.md) · [Evidence Q&A](docs/evidence_qa_mvp.md) · [Docs index](docs/README.md) · [Developer guide](AGENTS.md)

## Product Workflow

```text
Research brief + local evidence
→ Literature RAG and source-passage evidence
→ Auto Scientist idea generation
→ Safe registered or approval-gated generated-code experiments
→ Experiment tree search and selected-node reruns
→ Paper writing, citation binding, LaTeX/PDF compile report
→ Simulated reviewer, revision plan, and human approval gates
→ Evidence Trust Package export
```

The web workspace exposes this as an AI-Scientist-style console with Ideas, Experiments, Code Review, Paper, and Trust areas. Long-running local Auto Scientist runs can be started as jobs, polled through event timelines/SSE, cancelled cooperatively, and exported with logs and artifacts.

## What v3.0.0-rc1 Includes

| Area | Current status | Integrity boundary |
| --- | --- | --- |
| Literature RAG | Offline local keyword/FTS/hybrid retrieval | Answers cite source passages or mark unsupported |
| Evidence Q&A | `supported`, `weakly_supported`, `unsupported` answer contract | Unsupported answers are safety outcomes, not hidden failures |
| Auto Paper Writer | Plan, outline, Markdown, LaTeX draft artifacts | Drafts are AI-generated and require human review |
| Auto Scientist | Ideas, experiment plans, registered experiments, generated-code proposals, optional sandbox execution, experiment tree search | No arbitrary unchecked code execution; code proposals are reviewable and approval-gated where configured |
| Job system | Local background job records, logs, event timelines, SSE stream, cooperative cancellation | Local MVP, not distributed production queueing |
| Experiment-tree workflow | Select/rerun nodes, rewrite paper from selected/best node, generate revision plan | Heuristic scores are workflow signals, not scientific validity metrics |
| Claim/citation binding | Bind manuscript claims to experiment results and paper sentences to local source passages | Citation binding is not citation verification guarantee |
| Compile pipeline | LaTeX compile when compiler is available, fallback preview PDF otherwise | Preview PDF is not a formal publication artifact |
| Human Review Queue | Aggregates metadata, parser, claim, code, job, revision, citation, and compile risks | Approval records local decisions; they do not certify scientific truth |
| Evidence Trust Package | Exportable zip with manifests, hashes, logs, artifacts, review state, and limitations | Audit handoff package, not compliance certificate |

## Five-Minute Local Start

Backend:

```bash
cd services/api
python -m pip install -e . pytest
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd apps/web
npm ci
npm run dev -- --hostname 127.0.0.1 --port 3100
```

Open `http://127.0.0.1:3100`. The API health endpoint is `http://127.0.0.1:8000/health` and reports `v3.0.0-rc1`.

Local defaults are mock/offline-first:

```bash
cp .env.example .env
# LLM_MODE=mock is the default; no API key is required for tests or demos.
```

## End-to-End Auto Scientist Demo

Run the local demo from seeded project to evidence trust package:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python scripts/run_auto_scientist_demo.py \
  --project-id demo_auto_scientist_v3 \
  --max-ideas 1 \
  --max-experiments-per-idea 1 \
  --generated-code \
  --tree-search \
  --output /tmp/researchagent_auto_scientist_demo.json

python scripts/validate_v38.py \
  --demo-report /tmp/researchagent_auto_scientist_demo.json \
  --output /tmp/researchagent_validate_v38.json
```

The demo validates expected local artifacts such as RAG answers, generated-code sandbox outputs, experiment tree, Auto Scientist manuscript, experiment-claim bindings, paper-citation bindings, compile report, human review queue, and evidence trust package. Passing this demo means the local workflow generated expected artifacts; it does not mean the generated paper is scientifically valid.

## Verification Matrix

Run the release-candidate checks locally:

```bash
python -m compileall services/api scripts
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest services/api/tests -q
python scripts/evaluate_local_researchagent.py --output /tmp/researchagent_local_eval.json
python scripts/check_secrets_static.py
python scripts/validate_v38.py
python scripts/package_release.py --version v3.0.0-rc1 --output-dir /tmp/researchagent_dist
cd apps/web && npm ci && npm run typecheck && NEXT_TELEMETRY_DISABLED=1 npm run build
```

Optional E2E UI checks require a Playwright browser installation:

```bash
cd apps/web
npx playwright install chromium
npx playwright test --project=chromium
```

## Repository Layout

```text
services/api/       FastAPI backend, tools, Auto Scientist APIs, workflows, tests
apps/web/           Next.js AI-Scientist-style workspace UI and Playwright specs
scripts/            Demo, eval, validation, packaging, and local verification utilities
docs/               Product, architecture, roadmap, release-readiness, and archived reports
evals/              Local demo evaluation fixtures
.github/            CI, issue templates, and pull request template
projects/           Local runtime workspace, ignored by git
dist/               Local release output, ignored by git
reports/            Local verification reports, ignored by git
```

## Research Integrity And Safety Rules

- `LLM_MODE=mock` is the default.
- Tests and demos must not require real API keys, external networks, or external research services.
- Generated-code experiments are registered, sandboxed, reviewable, and/or approval-gated depending on settings.
- Do not fabricate DOI values, authors, years, journals, pages, p-values, significance, causal claims, experimental conclusions, or verified references.
- Do not present mock/demo output as real scientific evidence.
- Preserve evidence, provenance, source passages, experiment outputs, code proposals, job events, audit logs, reviewer issues, human decisions, and limitations.
- Use project-relative paths in artifacts and release packages.
- Do not include secrets, local absolute paths, runtime databases, caches, `node_modules`, `.next`, generated projects, or release zips in source packages.
- Do not claim production readiness, compliance readiness, peer review readiness, publication acceptance, external benchmark performance, or scientific proof.

## Current Limitations

- This is a local-first release candidate, not a hosted production service.
- Auto Scientist runs are local workflow artifacts and require human review.
- Sandbox safety is a defense-in-depth layer, not a guarantee that arbitrary code is safe.
- Docker sandbox behavior must be verified on machines with Docker daemon and approved local images.
- Literature parsing, RAG, citation binding, and source locators depend on local parser quality and metadata review.
- Current local evals are regression fixtures, not public scientific benchmarks.
- Reviewer output is simulated and cannot replace peer review, domain expertise, ethics review, or statistical review.

## Release Readiness

Use [docs/release_v3.md](docs/release_v3.md) and [docs/github_release_checklist.md](docs/github_release_checklist.md) before publishing a release candidate. Source and evidence packages should be produced with:

```bash
python scripts/package_release.py --version v3.0.0-rc1 --output-dir dist
```

## License

License: TBD by repository owner.

## Historical Validation Notes

Historical validation scripts still assert earlier milestone labels. Those reports are archived under `docs/`; the current release-candidate narrative is `v3.0.0-rc1`.

- ResearchAgent v1.0 Local MVP: `python scripts/validate_v1.py`
- ResearchAgent v2.0 Research Workspace scaffold: `python scripts/validate_v2.py`
- ResearchAgent v3.0 release candidate: `python scripts/validate_v38.py`
