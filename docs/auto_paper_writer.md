# Auto Paper Writer MVP

ResearchAgent now includes an **Auto Paper Writer MVP** for generating an auditable manuscript draft from project-local evidence. It is inspired by open-source research-writing systems, but deliberately keeps ResearchAgent's local/offline and integrity boundaries:

- AI-Scientist / AI-Scientist-v2: idea → experiment/result → writeup → simulated review loop.
- STORM: knowledge curation → outline → article generation → polishing.
- PaperQA2: source-passage evidence gathering and citation-grounded answers.
- GPT Researcher: planner → research execution → publisher/report separation.
- AutoSurvey/AutoResearch-style workflows: structured survey/paper planning, generation, assembly, and evaluation.

This implementation is not an autonomous scientific-discovery system. It does not execute LLM-generated code, run experiments, claim novelty, claim peer review, or claim that references are verified.

## What It Does

The Auto Paper Writer turns a local ResearchAgent project into a draftable artifact chain:

```text
local literature + RAG chunks + analysis artifacts + figure provenance
  → manuscript/paper_plan.json
  → manuscript/outline.json
  → manuscript/sections/*.md
  → manuscript/draft_full.md
  → provenance/claim_audit.json
  → manuscript/draft_full.tex
```

The goal is to produce a useful first draft while making evidence gaps visible. Every output is a draft artifact requiring human review.

## API

Generate a paper plan:

```bash
POST /api/projects/{project_id}/paper-writer/plan
```

Optional JSON body:

```json
{
  "paper_type": "research_article",
  "topic": "local evidence synthesis",
  "research_question": "What does the local evidence support?",
  "retrieval_mode": "local_hybrid_fts"
}
```

Generate an outline:

```bash
POST /api/projects/{project_id}/paper-writer/outline
```

Generate a full Markdown draft:

```bash
POST /api/projects/{project_id}/paper-writer/draft
```

Export LaTeX source:

```bash
POST /api/projects/{project_id}/paper-writer/export-latex
```

Read status:

```bash
GET /api/projects/{project_id}/paper-writer/status
```

## Artifacts

### `manuscript/paper_plan.json`

Includes:

- `schema_version`
- `paper_type`
- `title_candidates`
- `research_question`
- `thesis_summary`
- `target_sections`
- `required_evidence`
- `available_evidence_summary`
- `missing_evidence_warnings`
- `human_inputs_required`
- `design_inspirations`

### `manuscript/outline.json`

Includes one record per planned section:

- `section_id`
- `title`
- `purpose`
- `required_claims`
- `required_evidence_types`
- `source_passage_ids`
- `source_locators`
- `support_status`
- `status`

Statuses:

- `ready`: strong local evidence signal, but still requires human review.
- `weak_evidence`: local passages matched, but metadata or parser quality limits confidence.
- `missing_evidence`: no local support; the section must be written as a TODO or limitation.

### `manuscript/draft_full.md`

A Markdown draft with an explicit notice:

```text
AI-generated draft from local project evidence. Requires human review before external use.
```

The draft is generated section-by-section and avoids unverified statistical, causal, novelty, peer-review, publication-readiness, or reference-verification claims.

### `manuscript/writing_audit.json`

Summarizes generated sections, source-passage bindings, missing evidence, human-review requirements, and claim-audit integration.

### `manuscript/writing_rounds.jsonl`

Records each generated section as a local writing round.

### `manuscript/draft_full.tex`

A simple LaTeX source export. It does not compile PDF and does not generate verified references.

## Writing Contract

The writer follows these rules:

1. Each substantive paragraph must be tied to source passages, local analysis artifacts, figure provenance, or be marked as unsupported/TODO.
2. It must not fabricate DOI values, authors, years, journals, pages, p-values, statistical significance, causal conclusions, experiments, or verified references.
3. Missing evidence is written as a limitation or TODO, not as a conclusion.
4. The generated draft must be labeled as AI-generated and requiring human review.
5. It does not overwrite the user's official `manuscript/draft.md`.
6. It runs claim audit after draft generation when possible.
7. It uses project-relative paths only.

## What It Does Not Do

The Auto Paper Writer is **not**:

- a paper-writing service for bypassing human authorship responsibilities,
- peer review,
- citation verification,
- a scientific truth oracle,
- a system for fabricating results,
- an automatic submission tool,
- a replacement for human review, lab records, statistical review, or ethics review.

## Recommended Local Flow

```bash
python scripts/seed_demo.py
python scripts/run_demo.py
cd services/api
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Then call the endpoints above or use the frontend API client functions:

- `createPaperWriterPlan`
- `createPaperWriterOutline`
- `createPaperWriterDraft`
- `exportPaperWriterLatex`
- `getPaperWriterStatus`

## Verification

Focused backend tests:

```bash
python -m pytest services/api/tests/test_v24_paper_writer_plan.py \
  services/api/tests/test_v24_paper_writer_draft.py \
  services/api/tests/test_v24_latex_export.py -q
```

Full backend check:

```bash
python -m compileall services/api scripts
python -m pytest services/api/tests -q
```
