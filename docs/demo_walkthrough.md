# Demo Walkthrough

This walkthrough demonstrates the local `v2.0.1-dev` ResearchAgent workspace. It uses mock/offline defaults and does not claim real scientific findings, verified references, statistical significance, or publication readiness.

## 1. Prepare The Demo Workspace

```bash
python scripts/reset_demo.py --yes
python scripts/seed_demo.py
```

The demo project is written under `projects/demo_project`, which is ignored by git.

## 2. Run The Local Workflow

```bash
python scripts/run_demo.py
```

Expected artifact groups include:

- literature index and local RAG records
- analysis summaries and provenance
- figure provenance
- evidence and claim alignment records
- manuscript draft/refinement artifacts
- reviewer and revision records
- audit log and run history

These outputs are local demo artifacts and must not be presented as real research conclusions.

## 3. Start The Apps

Backend:

```bash
cd services/api
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd apps/web
npm run dev -- --hostname 127.0.0.1 --port 3100
```

Open `http://127.0.0.1:3100`.

## 4. Review The Command Center

The homepage now starts with the ResearchAgent Command Center:

1. Project Setup
2. Knowledge & Evidence Index
3. Research & Analysis
4. Manuscript & Review Loop
5. Export & Trust Report

The older detailed panels remain available under Advanced / Diagnostics so existing audit tools are not removed.

## 5. Validate

```bash
python -m pytest services/api/tests -q
python scripts/validate_v2.py
cd apps/web && npm run typecheck
cd apps/web && npm run build
```

## 6. Package A Release Candidate

```bash
python scripts/package_release.py --version v2.0.1-dev --output-dir dist
```

Review `dist/researchagent-v2.0.1-dev-source.zip` and `dist/researchagent-v2.0.1-dev-evidence.zip`. Source packages should not include runtime projects, caches, local databases, `.env*`, Node build output, or Playwright reports.
