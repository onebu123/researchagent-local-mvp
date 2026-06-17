# Demo Walkthrough

This walkthrough demonstrates the local `v3.0.0-rc1` ResearchAgent workspace. It uses mock/offline defaults and placeholder literature. It does not claim real scientific findings, verified references, statistical significance, or publication readiness.

## Reset And Run

```bash
python scripts/reset_demo.py --yes
python scripts/seed_demo.py
python scripts/run_demo.py
```

`run_demo.py` seeds a local demo project, runs the workflow, builds local RAG artifacts, asks one RAG question, generates source-passage evidence, runs mock metadata/reference checks, and creates citation reports.

## Expected Artifact Areas

```text
projects/demo_project/
  literature/
  literature/rag/
  analysis/
  figures/
  provenance/
  manuscript/
  reviews/
  runs/
  llm/
```

Important files include:

- `literature/literature_index.json`
- `literature/rag/chunks.jsonl`
- `literature/rag/rag_answers.jsonl`
- `analysis/result_summary.json`
- `analysis/analysis_provenance.json`
- `figures/figure_provenance.json`
- `provenance/evidence.json`
- `provenance/claim_alignment.json`
- `manuscript/draft.md`
- `manuscript/readable.md`
- `manuscript/refined.md`
- `reviews/review_report.json`
- `runs/run_history.json`

## Local Verification

For the full local check, run:

```bash
python scripts/verify_local.py
```

The verifier writes:

- `reports/verification_report.json`
- `reports/verification_report.md`

The report records command results, artifact existence, JSON parsing, review report checks, RAG provenance checks, safety scans, release package checks, known limitations, and final status.

## Web Demo

Start the API and web app:

```bash
cd services/api
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

```bash
cd apps/web
npm run dev -- --hostname 127.0.0.1 --port 3100
```

Open `http://127.0.0.1:3100`. The first screen is the ResearchAgent Command Center.

## Release Package Demo

```bash
python scripts/package_release.py --version v3.0.0-rc1 --output-dir dist
```

Review:

- `dist/researchagent-v3.0.0-rc1-source.zip`
- `dist/researchagent-v3.0.0-rc1-evidence.zip`

These packages are local audit artifacts. They are not compliance, production, or peer review certificates.
