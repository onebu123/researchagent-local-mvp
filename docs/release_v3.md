# v3.0.0-rc1 Release Readiness

ResearchAgent `v3.0.0-rc1` is a local-first AI-Scientist-style release candidate. It demonstrates an auditable workflow from local evidence to sandboxed experiment diagnostics, manuscript generation, simulated review, human approval, and evidence trust package export.

## Release Candidate Scope

The release candidate includes:

- local Literature RAG and Evidence Q&A with supported/weakly-supported/unsupported answer status
- Auto Paper Writer plan, outline, Markdown, and LaTeX draft artifacts
- Auto Scientist idea generation and experiment planning
- registered safe experiment templates
- generated-code proposal lifecycle with static scan, source hash, approval gate, optional subprocess/Docker sandbox, and rerun records
- deterministic experiment tree search, node selection, node reruns, and selected-node paper rewrites
- best-node-driven revision plan and human-approved patch application
- experiment result to manuscript claim bindings
- paper citation/source-passage bindings
- LaTeX compile report with fallback preview PDF
- job records, logs, event timelines, SSE event stream, and cooperative cancellation
- Human Review Queue and Evidence Trust Package export
- end-to-end demo and validation scripts

## Required Local Checks

Run these before cutting a release candidate:

```bash
python -m compileall services/api scripts
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest services/api/tests -q
python scripts/evaluate_local_researchagent.py --output /tmp/researchagent_local_eval.json
python scripts/check_secrets_static.py
python scripts/validate_v38.py
python scripts/package_release.py --version v3.0.0-rc1 --output-dir /tmp/researchagent_dist
cd apps/web && npm ci && npm run typecheck && NEXT_TELEMETRY_DISABLED=1 npm run build
```

Optional browser E2E checks:

```bash
cd apps/web
npx playwright install chromium
npx playwright test --project=chromium
```

## End-to-End Demo Check

Run the local Auto Scientist demo and validate the generated report:

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

A passing demo report means expected local artifacts were generated. It does not certify scientific correctness, citation verification, peer review, statistical validity, or publication readiness.

## Version Surface Checklist

`v3.0.0-rc1` must appear consistently in:

- `README.md`
- `CHANGELOG.md`
- `services/api/main.py`
- `services/api/pyproject.toml` as `3.0.0rc1`
- `apps/web/package.json`
- `apps/web/package-lock.json`
- `apps/web/features/workspace/useWorkspaceData.ts`
- `apps/web/lib/api/legacy.ts`
- `scripts/package_release.py`
- `scripts/collect_evidence.py`
- `scripts/verify_local.py`
- `docs/github_release_checklist.md`

## Package Hygiene

Source and evidence packages must exclude:

- `.git/`
- `.env` and `.env.*` except `.env.example`
- `projects/`
- `dist/`
- `reports/`
- `node_modules/`
- `.next/`
- caches, test reports, local databases, and generated zips

Generated package entries must use POSIX relative paths and must not include local absolute paths or secret-like values.

## Non-Goals

This release candidate does not claim:

- hosted production readiness
- formal peer review
- citation verification guarantee
- compliance certification
- publication acceptance
- automated scientific correctness
- external benchmark performance
