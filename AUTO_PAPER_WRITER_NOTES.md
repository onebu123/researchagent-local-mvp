# Auto Paper Writer completion notes

This handoff adds an evidence-grounded Auto Paper Writer MVP inspired by open research-writing systems such as AI-Scientist/AI-Scientist-v2, STORM, PaperQA-style evidence gathering, and planner/publisher research-report architectures.

## What changed

- Added `services/api/app/tools/paper_writer/` with planning, outline, section drafting, citation binding, safety contract, LaTeX export, and writer-eval helpers.
- Added `services/api/app/api/paper_writer.py` and registered the router in `services/api/main.py`.
- Added request schemas for Auto Paper Writer API calls.
- Added frontend API client/types for paper-writer endpoints.
- Added backend tests for plan, draft, and LaTeX generation.
- Added `docs/auto_paper_writer.md` and links from README/docs index.

## New API endpoints

- `POST /api/projects/{project_id}/paper-writer/plan`
- `GET /api/projects/{project_id}/paper-writer/plan`
- `POST /api/projects/{project_id}/paper-writer/outline`
- `GET /api/projects/{project_id}/paper-writer/outline`
- `POST /api/projects/{project_id}/paper-writer/draft`
- `GET /api/projects/{project_id}/paper-writer/draft`
- `POST /api/projects/{project_id}/paper-writer/export-latex`
- `GET /api/projects/{project_id}/paper-writer/status`

## New artifacts

- `manuscript/paper_plan.json`
- `manuscript/outline.json`
- `manuscript/sections/*.md`
- `manuscript/draft_full.md`
- `manuscript/draft_full.tex`
- `manuscript/writing_audit.json`
- `manuscript/writing_rounds.jsonl`

## Boundaries

- No external API, network dependency, or live LLM requirement was added.
- The writer does not execute LLM-generated code.
- The writer does not overwrite `manuscript/draft.md`.
- The writer does not fabricate DOI values, authors, years, journals, p-values, statistical significance, causal claims, experiments, verified references, peer review, or publication readiness.
- Generated drafts are explicitly labeled as AI-generated and requiring human review.

## Verification run in this environment

```bash
python -m compileall services/api scripts
python -m pytest services/api/tests -q
python scripts/evaluate_local_researchagent.py --output /tmp/researchagent_local_eval_autopaper.json
python scripts/check_secrets_static.py
python scripts/package_release.py --version v2.0.1-dev --output-dir /tmp/researchagent_autopaper_dist
```

Results:

- Backend tests: `196 passed`
- Local eval: `total=3, passed=3, failed=0`
- Static secret scan: passed
- Release package script: generated source and evidence zips

## Remaining product work

- Build a focused frontend UI for Auto Paper Writer instead of only API client functions.
- Add a larger writing eval suite for section quality, evidence binding, and hallucination prevention.
- Add line-level draft comparison and approve/apply workflows for generated draft sections.
- Add optional local-only PDF/OCR improvements before relying on page locators in generated citations.
