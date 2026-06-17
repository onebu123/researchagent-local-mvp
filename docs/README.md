# ResearchAgent Docs

This directory contains current project-facing documentation plus archived milestone evidence. The current repository version is `v3.0.0-rc1`.

## Start Here

- [v3.0 release readiness](release_v3.md): release-candidate scope, validation matrix, package hygiene, and non-goals.
- [Product vision](product_vision.md): who ResearchAgent is for, what problem it solves, and what it does not solve.
- [System architecture](architecture.md): backend, frontend, artifact, verification, and release-package structure.
- [Agent architecture](agent_architecture.md): intended agent responsibilities, inputs, outputs, and safety boundaries.
- [Evidence Q&A MVP](evidence_qa_mvp.md): local Literature RAG support status, source passages, FTS modes, and offline eval.
- [Draft Claim Audit](draft_claim_audit.md): manuscript claim support checks against local source passages.
- [Auto Paper Writer](auto_paper_writer.md)
- [Auto Scientist MVP](auto_scientist.md): safe local idea generation, registered/sandboxed experiment execution, deterministic code-writer strategies, generated-code approval gates, reviewer-style code diagnostics, optional Docker sandbox mode, job/progress artifacts, deterministic experiment tree search, best-node revision loops, experiment-to-manuscript claim bindings, result analysis, paper drafting, and simulated review.
- [Auto Scientist End-to-End Demo](auto_scientist_end_to_end_demo.md): one-command local run from seeded project to job timeline, experiment tree, manuscript, citation/experiment bindings, compile report, human review queue, and trust package.
- [Human Review Queue](human_review_queue.md): unified local review queue for metadata, PDF quality, claims, reviewer issues, and patches.
- [Evidence-grounded Revision Plan](revision_loop.md): patch suggestions that require human approval.
- [Evidence Trust Package](evidence_trust_package.md): exportable local audit handoff package.
- [Local Evaluation](evaluation.md): offline RAG and claim-audit regression evals.
- [Roadmap](roadmap.md): v3.0.0-rc1 through v3.0 goals, deliverables, acceptance criteria, and non-goals.
- [Demo walkthrough](demo_walkthrough.md): local mock/offline demo flow and expected artifacts.
- [GitHub release checklist](github_release_checklist.md): source/evidence package and repository hygiene checks.
- [Maintainer runbook](maintainer_runbook.md): release checks, provider usage, failure records, manual review, and prohibited claims.
- [Deployment scaffold](deployment_v2.md): optional local planning scaffold for future deployment work.
- [Local MVP limitations](local_mvp_limitations.md): what the current system does not guarantee.
- [User guide](user_guide.md): current local workspace usage notes.
- [Developer agent guide](../AGENTS.md): maintenance rules for AI coding agents.

## Historical Material

Historical v0.x, v1.x, and v2.0 acceptance criteria/reports remain in this directory for auditability. They are not the current homepage narrative. Use [archive.md](archive.md) as the index before reading old milestone reports.

Legacy AI-agent constraints are preserved at [archive/legacy_agent_constraints.md](archive/legacy_agent_constraints.md).

- Auto Scientist job event timelines, generated-code reruns, experiment-tree node workflows, and best-node revision loops, and experiment-claim bindings are documented in [Auto Scientist MVP](auto_scientist.md).

- [Citation binding and compile pipeline](citation_compile_pipeline.md)
