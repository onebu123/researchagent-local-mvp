# Auto Scientist MVP

Auto Scientist is the safe local ResearchAgent path for an AI-Scientist-style loop:

`ideas -> safe registered experiments -> result analysis -> full manuscript writeup -> simulated reviewer -> human review queue`

It is inspired by automated scientific discovery systems such as AI-Scientist, but the local MVP intentionally avoids unrestricted autonomous code execution. It runs only registered local experiment templates and records `arbitrary_code_execution=false` in run artifacts.

## What it does

- Generates local research ideas from project evidence artifacts.
- Builds an experiment plan from safe registered templates.
- Runs local evidence inventory, retrieval evaluation, claim audit evaluation, descriptive data profiling, and writing safety checks.
- Analyzes experiment outputs and writes an Auto Scientist report.
- Can generate an evidence-grounded paper plan, outline, Markdown draft, LaTeX draft, and a full Auto Scientist manuscript that summarizes experiment outputs.
- Preserves audit events, project-relative artifact paths, and human-review limitations.

## What it does not do

- It does not execute arbitrary LLM-generated code.
- It does not invent experiments, DOI values, verified references, p-values, statistical significance, causal effects, or experimental results.
- It is not peer review, publication readiness, or scientific proof.
- It does not submit papers or bypass human research judgment.

## API

```text
POST /api/projects/{project_id}/auto-scientist/ideas
GET  /api/projects/{project_id}/auto-scientist/ideas
POST /api/projects/{project_id}/auto-scientist/run
GET  /api/projects/{project_id}/auto-scientist/status
GET  /api/projects/{project_id}/auto-scientist/runs
```

Example payload:

```json
{
  "topic": "local evidence synthesis",
  "research_question": "What does the local evidence support?",
  "max_ideas": 3,
  "max_experiments_per_idea": 2,
  "paper_type": "research_article",
  "retrieval_mode": "local_hybrid_fts",
  "write_paper": true,
  "export_latex": true
}
```

## Artifacts

```text
auto_scientist/ideas.json
auto_scientist/experiment_plan.json
auto_scientist/runs.jsonl
auto_scientist/latest_run.json
auto_scientist/analysis.json
auto_scientist/auto_scientist_report.md
auto_scientist/scientist_review.json
auto_scientist/scientist_review.md
auto_scientist/paper_audit.json
manuscript/auto_scientist_paper.md
manuscript/auto_scientist_paper.tex
auto_scientist/experiments/<run_id>/<experiment_id>/experiment_result.json
auto_scientist/experiments/<run_id>/<experiment_id>/metrics.json
auto_scientist/experiments/<run_id>/<experiment_id>/summary.md
```

If paper writing is enabled, the loop also produces the Auto Paper Writer artifacts:

```text
manuscript/paper_plan.json
manuscript/outline.json
manuscript/draft_full.md
manuscript/draft_full.tex
manuscript/auto_scientist_paper.md
manuscript/auto_scientist_paper.tex
manuscript/writing_audit.json
auto_scientist/paper_audit.json
provenance/claim_audit.json
```

## Safe experiment templates

The MVP includes these registered templates:

- `evidence_inventory`
- `rag_retrieval_eval`
- `claim_audit_eval`
- `descriptive_data_profile`
- `writing_safety_eval`

Each template writes structured outputs under `auto_scientist/experiments/` and must remain offline/local by default.

## Recommended local flow

```bash
python scripts/seed_demo.py
python scripts/run_demo.py
# then call POST /api/projects/demo_project/auto-scientist/run
```

Review `auto_scientist/scientist_review.md`, `manuscript/draft_full.md`, and `provenance/claim_audit.json` before using any generated draft externally.


## AI-Scientist-style scope

This module follows the high-level pattern used by autonomous scientist systems:

1. propose ideas from local evidence,
2. plan experiments,
3. run experiments,
4. analyze results,
5. write a manuscript,
6. simulate a reviewer, and
7. route remaining risks to human review.

The local MVP deliberately differs from heavy autonomous-discovery systems in one important way: it does **not** execute arbitrary LLM-generated code. Experiment execution is restricted to registered templates such as `evidence_inventory`, `rag_retrieval_eval`, `claim_audit_eval`, `descriptive_data_profile`, and `writing_safety_eval`. This makes the first product version safer and reproducible while preserving the end-to-end research loop shape.

The full manuscript artifacts are:

```text
manuscript/auto_scientist_paper.md
manuscript/auto_scientist_paper.tex
auto_scientist/paper_audit.json
```

These files summarize local experiment outputs and related writing artifacts. They remain AI-generated drafts that require human review before external use.

## Sandboxed generated-code experiment manager

The next step toward an AI-Scientist-style system is an optional generated-code experiment manager. It is **off by default**. When explicitly enabled with `allow_generated_code_experiments=true`, the loop adds a `generated_code_smoke_test` experiment that writes generated Python source under:

```text
auto_scientist/generated_code/<run_id>/<experiment_id>/experiment.py
```

The generated source is not run directly. It first passes a conservative static scan that rejects network, subprocess, unsafe filesystem, dynamic import, `eval`, `exec`, `open`, and similar escape primitives. Approved code then runs in an isolated Python subprocess using `python -I -S`, project-local inputs, no inherited Python site packages, wall-clock timeout, and local artifact capture. The runner records:

```text
auto_scientist/generated_code/<run_id>/<experiment_id>/input.json
auto_scientist/generated_code/<run_id>/<experiment_id>/stdout.txt
auto_scientist/generated_code/<run_id>/<experiment_id>/stderr.txt
auto_scientist/generated_code/<run_id>/<experiment_id>/outputs/result.json
auto_scientist/generated_code/<run_id>/<experiment_id>/outputs/metrics.json
auto_scientist/generated_code/<run_id>/<experiment_id>/outputs/summary.md
auto_scientist/generated_code/<run_id>/<experiment_id>/sandbox_result.json
```

Generated-code runs remain local research diagnostics, not independent scientific proof. They are routed to the Human Review Queue and Evidence Trust Package so a user can inspect source, static-scan results, stdout/stderr, metrics, and limitations before using any results externally.

Example payload:

```json
{
  "topic": "local generated-code experiment manager",
  "max_ideas": 1,
  "max_experiments_per_idea": 1,
  "write_paper": true,
  "export_latex": true,
  "allow_generated_code_experiments": true,
  "generated_code_timeout_seconds": 5,
  "generated_code_max_memory_mb": 512
}
```

This is still a safety MVP. A future stronger version should add a real container sandbox, disabled network namespace, CPU/memory quotas enforced outside Python, optional GPU runners, static dependency allowlists, approval gates before execution, and rerun/revise search over experiment variants.

## Optional Docker sandbox mode

Generated-code experiments can request a stronger Docker-based runner by setting:

```json
{
  "allow_generated_code_experiments": true,
  "generated_code_sandbox_mode": "docker",
  "generated_code_docker_image": "python:3.11-slim"
}
```

Docker mode is still explicit opt-in and still requires the same static scan. It also:

- checks that Docker is installed and the daemon is reachable,
- checks that the requested image is already present locally,
- never pulls images automatically,
- runs with `--network none`, memory and process limits, a read-only container filesystem, and a project-local mounted workspace,
- records `network_disabled_by_docker`, `docker_image`, stdout/stderr, generated source, inputs, outputs, and `sandbox_result.json`.

If Docker or the requested local image is unavailable, the experiment reports `status="docker_unavailable"` and the Auto Scientist loop continues with reviewable artifacts. This prevents CI, offline laptops, or restricted local environments from failing just because Docker is not installed.

Docker mode is safer than the Python subprocess fallback, but it is still not a proof that generated code is scientifically valid. Users must review generated source, static-scan output, sandbox policy, stdout/stderr, metrics, and resulting manuscript claims.

## Deterministic experiment tree search

The loop can also run a bounded local experiment tree search:

```json
{
  "enable_experiment_tree_search": true,
  "experiment_tree_max_depth": 1,
  "experiment_tree_branching_factor": 2
}
```

This writes:

```text
auto_scientist/experiment_tree.json
auto_scientist/experiment_tree.md
```

The tree search expands the highest-scoring local experiment node using registered safe templates and, if explicitly enabled, sandboxed generated-code candidates. Scores are deterministic product heuristics based on completion status, claim support status, and retrieval/evaluation signals. They are **not** measures of scientific validity.

Human Review Queue includes an `auto_scientist_experiment_tree_review` item when tree search runs, and Evidence Trust Package includes the tree artifacts. Review the selected best node and child experiment outputs before using the resulting manuscript externally.

## Generated-code source lifecycle and approval gate

Generated-code experiments now have a reviewable source lifecycle:

```text
source candidate generation
→ code_proposal.json
→ static scan
→ optional human approval gate
→ sandbox execution
→ stdout/stderr/result capture
→ optional conservative revision/rerun
```

The source generator supports these modes:

- `deterministic`: default local source, no LLM call.
- `mock_llm`: routes through the existing LLM client contract but remains mock/fallback unless live mode is configured.
- `live_llm`: optional live synthesis through the configured OpenAI-compatible endpoint.

LLM/provided source is treated as untrusted candidate code. It can require a recorded approval before execution:

```json
{
  "allow_generated_code_experiments": true,
  "generated_code_source_mode": "mock_llm",
  "generated_code_requires_approval": true
}
```

Pending candidates write `auto_scientist/generated_code/<run_id>/<experiment_id>/code_proposal.json` and return `status="pending_human_approval"` rather than executing. A local user can record a decision with:

```text
POST /api/projects/{project_id}/auto-scientist/generated-code/approvals
GET  /api/projects/{project_id}/auto-scientist/generated-code/approvals
```

The approval record includes run id, experiment id, source hash, decision, reason, reviewer, and timestamp. Approval is a local workflow gate, not a statement that the code or result is scientifically valid.

## Docker image allowlist

Docker sandbox mode uses an image allowlist. The default allowlist is:

```text
python:3.11-slim
```

It can be configured locally with:

```text
AUTO_SCIENTIST_DOCKER_IMAGE_ALLOWLIST=python:3.11-slim
```

Images outside the allowlist are rejected before Docker execution, and images are never pulled automatically. The policy snapshot is written to:

```text
auto_scientist/docker_image_policy.json
```

## Conservative generated-code revision loop

The Auto Scientist run can optionally perform a bounded reviewer → code revision → rerun loop for generated-code failures:

```json
{
  "allow_generated_code_experiments": true,
  "enable_generated_code_revision_loop": true,
  "generated_code_revision_rounds": 1
}
```

This first MVP does not perform unrestricted autonomous code repair. It replaces failed, timed-out, rejected, or approval-blocked generated-code experiments with a deterministic safe diagnostic script and runs it through the same sandbox contract. Revision records are stored in:

```text
auto_scientist/code_revision_rounds.jsonl
```

The Human Review Queue and Evidence Trust Package include these revision artifacts so users can inspect parent failures, revised source, and rerun results.

## Experiment code writer strategies

Generated-code experiments now use a deterministic local experiment-code writer by default. This is still not arbitrary autonomous code execution; the writer emits bounded scripts that read `input.json` and write only `outputs/result.json`, `outputs/metrics.json`, and `outputs/summary.md`.

The current strategies are:

- `lexical_diagnostics`: compute bounded lexical overlap between the research question and local evidence text.
- `retrieval_ablation`: score local source passages against the research question to inspect retrieval behavior.
- `claim_support_matrix`: compare manuscript/claim-audit claim text against local evidence snippets.
- `descriptive_table_profile`: summarize local analysis/table metadata without statistical testing.

Example:

```json
{
  "allow_generated_code_experiments": true,
  "generated_code_strategy": "retrieval_ablation"
}
```

All strategies remain local diagnostics. They do not establish scientific truth, statistical significance, causality, or citation verification.

## Reviewer-style code diagnostics

When generated-code experiments fail, time out, hit a static-scan violation, wait for approval, or cannot use Docker, the generated-code revision loop now records reviewer-style diagnostics in:

```text
auto_scientist/code_review_rounds.jsonl
```

Each diagnostic classifies the failure, records static-scan findings where available, and recommends a conservative revision strategy. The first safe repair strategy is still deterministic fallback code rather than open-ended autonomous patching.

## Local job/progress API

Long Auto Scientist runs can be invoked through the local job API. Two execution contracts are available:

```text
POST /api/projects/{project_id}/jobs/auto-scientist/run    # synchronous compatibility path
POST /api/projects/{project_id}/jobs/auto-scientist/start  # local background worker path
POST /api/projects/{project_id}/jobs/{job_id}/cancel       # cooperative cancellation request
GET  /api/projects/{project_id}/jobs
GET  /api/projects/{project_id}/jobs/{job_id}
GET  /api/projects/{project_id}/jobs/{job_id}/log
```

The background path returns a job record immediately and updates project-local artifacts as the workflow progresses:

```text
jobs/jobs.jsonl
jobs/latest_job.json
jobs/<job_id>.json
jobs/<job_id>.log
jobs/<job_id>.cancel.json
```

Cancellation is cooperative. The local worker checks cancellation at progress checkpoints, so an already-started sandbox subprocess or Docker run may finish or timeout before the job becomes `cancelled`. This is a local-MVP contract, not a distributed queue; it gives the frontend stable polling, log, and cancellation artifacts now and leaves room to swap the implementation for a real worker later.

## Auto Scientist Workbench UI

The homepage now includes an Auto Scientist Workbench as the primary product surface for the autonomous workflow:

```text
Configure brief and research question
→ Generate ideas
→ Run Auto Scientist job
→ Create approval-gated generated-code proposal
→ Review proposal source/static scan/source hash
→ Approve or reject generated-code candidate
→ Rerun after approval if execution is desired
→ Inspect job log, manuscript artifacts, review queue, and trust package outputs
```

The workbench uses these API endpoints:

```text
POST /api/projects/{project_id}/auto-scientist/ideas
POST /api/projects/{project_id}/jobs/auto-scientist/start
POST /api/projects/{project_id}/jobs/{job_id}/cancel
GET  /api/projects/{project_id}/auto-scientist/status
GET  /api/projects/{project_id}/jobs
GET  /api/projects/{project_id}/jobs/{job_id}/log
GET  /api/projects/{project_id}/auto-scientist/generated-code/proposals
GET  /api/projects/{project_id}/auto-scientist/generated-code/approvals
POST /api/projects/{project_id}/auto-scientist/generated-code/approvals
GET  /api/projects/{project_id}/human-review-queue
```

The generated-code proposals endpoint returns bounded review summaries, source hashes, static-scan status, approval state, artifact paths, and a truncated source excerpt. It is intended for local review UX; approving a proposal records a local workflow decision only. It does not certify that the code, experiment result, manuscript, or scientific claim is correct.


## v31 tabbed workflow UI

The workbench is organized into five product tabs:

```text
Ideas → Experiments → Code Review → Paper → Trust
```

The `Experiments` tab uses the background job API and polls active jobs until they reach a terminal state. It also exposes a cooperative `Cancel job` control. The `Code Review` tab lists generated-code proposals, source hashes, static-scan results, source excerpts, and approval/rejection actions. The `Paper` tab summarizes manuscript artifacts and reviewer outcome, while the `Trust` tab surfaces Human Review Queue items.

This UI still preserves safety wording: generated code requires review, generated manuscripts are draft artifacts, and demo/mock outputs are not scientific conclusions.

## v32 job event timeline and selected proposal rerun

Auto Scientist jobs now write a dedicated event timeline next to the job record:

```text
jobs/<job_id>.events.jsonl
```

The timeline records job creation, start, progress checkpoints, cancellation requests, and terminal status. The frontend can read or stream these events with:

```text
GET /api/projects/{project_id}/jobs/{job_id}/events
GET /api/projects/{project_id}/jobs/{job_id}/events/stream
```

The stream endpoint uses Server-Sent Events and is finite in the local MVP: it exits after a terminal job state has been observed and emitted. Clients can reconnect with `since_sequence` to resume from the last sequence number.

Background Auto Scientist jobs also forward internal loop checkpoints into the event timeline, including idea generation, experiment planning, per-experiment completion, analysis, manuscript writing, LaTeX export, and simulated reviewer stages. These events are product progress signals, not scientific validity signals.

Approved generated-code proposals can now be rerun directly after source-hash review:

```text
POST /api/projects/{project_id}/auto-scientist/generated-code/rerun
```

The rerun endpoint requires an existing proposal artifact, a matching source hash, and a latest approval decision of `approved` for that exact run/experiment/source hash. It then executes the approved proposal through the same subprocess or Docker sandbox contract and records:

```text
auto_scientist/generated_code_reruns.jsonl
```

Rerun success still does not certify the result. It only means an approved local code proposal executed under the configured sandbox and produced reviewable artifacts.

## v33 experiment tree node operations and paper rewrite

The experiment tree is now an interactive workflow artifact rather than a static report. Users can list nodes, select a node for manuscript emphasis, rerun a selected node, and rewrite the Auto Scientist manuscript from the selected or heuristic-best node.

New API endpoints:

```text
GET  /api/projects/{project_id}/auto-scientist/experiment-tree
GET  /api/projects/{project_id}/auto-scientist/experiment-tree/nodes
POST /api/projects/{project_id}/auto-scientist/experiment-tree/select
POST /api/projects/{project_id}/auto-scientist/experiment-tree/rerun-node
POST /api/projects/{project_id}/auto-scientist/experiment-tree/rewrite-paper
```

New artifacts:

```text
auto_scientist/experiment_tree_selection.json
auto_scientist/experiment_tree_reruns.jsonl
auto_scientist/paper_rewrites.jsonl
auto_scientist/latest_paper_rewrite.json
```

Selecting a node is a local workflow decision. It tells the paper writer which experiment candidate to emphasize, but it does not prove that the selected result is scientifically valid. Rerun outputs and rewritten manuscripts enter the Human Review Queue and Evidence Trust Package for inspection.

The Auto Scientist Workbench now exposes tree-node controls in the `Experiments` tab:

```text
View experiment tree nodes
→ Select best
→ Rerun node
→ Rewrite paper from node
```

The `Paper` tab can also rewrite the manuscript from the current selected/best node. Rewrites update:

```text
manuscript/auto_scientist_paper.md
manuscript/auto_scientist_paper.tex
auto_scientist/paper_audit.json
```

and preserve the selected-node decision in the paper audit and trust package. The rewritten manuscript remains an AI-generated draft requiring human review before any external use.

## v34 best-node-driven revision loop

The selected or heuristic-best experiment tree node can now drive a conservative manuscript revision loop:

```text
selected/best experiment tree node
→ reviewer-style critique
→ tree revision plan
→ human-approved patch suggestions
→ revised manuscript copy
→ claim audit rerun
→ evidence trust package refresh
```

New API endpoints:

```text
GET  /api/projects/{project_id}/auto-scientist/experiment-tree/revision-plan
POST /api/projects/{project_id}/auto-scientist/experiment-tree/revision-plan
POST /api/projects/{project_id}/auto-scientist/experiment-tree/apply-revision
```

New artifacts:

```text
auto_scientist/tree_revision_plan.json
auto_scientist/tree_revision_plan.md
auto_scientist/tree_revision_patches.json
auto_scientist/tree_revision_applications.jsonl
auto_scientist/latest_tree_revision_application.json
manuscript/auto_scientist_paper_revised.md
manuscript/auto_scientist_paper_revised.tex
```

The revision loop does **not** overwrite `manuscript/auto_scientist_paper.md`. It writes a revised copy under `manuscript/auto_scientist_paper_revised.md` after patch approval. Each patch has a review id such as:

```text
auto_scientist_tree_revision_patch_tree_revision_patch_001
```

The Human Review Queue must record an `approved` decision for the patch review id before the default apply endpoint will apply it. Applying a patch records a local workflow decision only; it is not peer review, not citation verification, and not proof that the selected experiment node is scientifically valid.

The Auto Scientist Workbench `Paper` tab now exposes:

```text
Rewrite from selected/best node
Generate revision plan
Apply approved patches
```

If claim-audit rerun is enabled, patch application reruns local claim audit against the revised manuscript copy. The application record and revised manuscript are included in the Evidence Trust Package.

## v35 experiment-result to manuscript-claim bindings

Auto Scientist manuscripts can now be traced sentence-by-sentence back to local experiment artifacts. This binding layer is designed to answer a reviewer-style question:

```text
Which experiment node, metric file, result claim, and output artifact supports this manuscript sentence?
```

New API endpoints:

```text
GET  /api/projects/{project_id}/auto-scientist/experiment-claim-bindings
POST /api/projects/{project_id}/auto-scientist/experiment-claim-bindings
```

New artifacts:

```text
auto_scientist/experiment_claim_bindings.json
auto_scientist/experiment_claim_bindings.md
auto_scientist/latest_experiment_claim_binding.json
auto_scientist/manuscript_claim_trace.jsonl
```

Each binding records the manuscript sentence, section, binding status, support status, matched experiment ids, matched tree node ids, metric keys, output artifacts, result-level claims, and warning flags. Binding statuses are:

```text
bound
weak_binding / weakly_bound
unbound
not_claim
```

A bound sentence is still not scientific proof. It only means the sentence can be traced to a local experiment artifact. Weakly bound or unbound sentences enter the Human Review Queue and should be revised, supported with additional local artifacts, or rewritten as limitations before external use. Generated-code bindings also require source hash, static scan, sandbox policy, stdout/stderr, and output review. The Auto Scientist Workbench `Paper` tab includes a `Bind claims to experiments` action and displays the current binding summary.


## Citation Binding and Compile Pipeline

Auto Scientist manuscripts can be passed through `POST /api/projects/{project_id}/auto-scientist/paper-citation-bindings` and `POST /api/projects/{project_id}/auto-scientist/paper-compile`. These workflows write paper-level citation binding, LaTeX compile report, and optional preview/compiled PDF artifacts. Source-passage-only bindings and preview PDFs require human review before external use. See [Citation binding and compile pipeline](citation_compile_pipeline.md).
