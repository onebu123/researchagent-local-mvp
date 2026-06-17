# Auto Scientist End-to-End Demo

This guide documents the deterministic local Auto Scientist demo added for the v37 productization pass. The demo is meant to prove that the local artifact chain can run from a seeded research workspace to an audit package. It is not a scientific-discovery benchmark, peer review, citation-verification guarantee, or publication-readiness certificate.

## What the demo runs

The command seeds a local demo project, builds literature RAG, asks a local evidence question, starts an Auto Scientist job, runs safe registered experiments plus optional sandboxed generated-code diagnostics, performs deterministic experiment-tree search, writes an Auto Scientist manuscript, binds manuscript claims to experiment outputs, binds paper claims/citations to local source passages, generates a LaTeX compile report or fallback preview PDF, selects a local experiment-tree node, rewrites the paper from that node, generates a best-node revision plan, builds the Human Review Queue, and exports an Evidence Trust Package.

The default demo uses local deterministic behavior:

```bash
python scripts/run_auto_scientist_demo.py --output /tmp/researchagent_auto_scientist_demo.json
```

Useful faster/smaller variants:

```bash
python scripts/run_auto_scientist_demo.py \
  --project-id demo_auto_scientist \
  --max-ideas 1 \
  --max-experiments-per-idea 1 \
  --generated-code \
  --tree-search \
  --output /tmp/researchagent_auto_scientist_demo.json
```

The script writes a JSON report and a Markdown companion report:

```text
/tmp/researchagent_auto_scientist_demo.json
/tmp/researchagent_auto_scientist_demo.md
```

## Expected core artifacts

A passing demo report checks for these project-relative artifacts:

```text
literature/literature_index.json
literature/rag/chunks.jsonl
literature/rag/rag_answers.jsonl
auto_scientist/ideas.json
auto_scientist/experiment_plan.json
auto_scientist/runs.jsonl
auto_scientist/latest_run.json
auto_scientist/analysis.json
auto_scientist/auto_scientist_report.md
auto_scientist/scientist_review.json
manuscript/auto_scientist_paper.md
manuscript/auto_scientist_paper.tex
auto_scientist/experiment_tree.json
auto_scientist/experiment_claim_bindings.json
manuscript/paper_citation_bindings.json
manuscript/latex_compile_report.json
trust/human_review_queue.json
exports/evidence_trust_package/manifest.json
```

Optional downstream artifacts may also exist:

```text
auto_scientist/experiment_tree_selection.json
auto_scientist/paper_rewrites.jsonl
auto_scientist/tree_revision_plan.json
auto_scientist/tree_revision_patches.json
manuscript/auto_scientist_paper_citation_bound.md
manuscript/auto_scientist_paper_preview.pdf
```

## Validation

Use `validate_v37.py` to validate that the Auto Scientist productization contract is present in source, tests, docs, API routes, and optionally a generated demo report.

Static/source validation:

```bash
python scripts/validate_v37.py
```

Validation with a generated demo report:

```bash
python scripts/run_auto_scientist_demo.py --output /tmp/researchagent_auto_scientist_demo.json
python scripts/validate_v37.py \
  --demo-report /tmp/researchagent_auto_scientist_demo.json \
  --output /tmp/researchagent_validate_v37.json
```

A passing validation means the expected local contracts and artifacts exist. It does not mean the generated manuscript is scientifically correct.

## Safety boundaries

- Generated code remains sandboxed and review-gated by policy.
- Docker mode does not auto-pull images and should use an allowlisted local image.
- Experiment tree scores are local workflow heuristics, not scientific validity scores.
- Citation binding links text to local passages; it does not verify citations externally.
- Fallback PDF preview is not a formal LaTeX compilation product.
- Human approvals are local workflow records, not peer review.
