# Product Vision

ResearchAgent aims to be an auditable all-in-one research agent workspace for literature ingestion, knowledge indexing, data analysis, evidence-grounded drafting, claim verification, reviewer simulation, revision planning, human approval, and exportable audit packages.

It is not a paper-writing service and must not fabricate research facts.

## Users

- Students learning evidence-grounded research workflows.
- Researchers organizing literature, data, drafts, and review issues.
- Labs that need local audit trails for claims, figures, citations, and revisions.
- Course projects that need reproducible demo evidence without live API keys.
- Draft reviewers who want to inspect provenance before approving text.

## Problems It Addresses

- Literature, notes, data, drafts, and reviewer feedback are often scattered across tools.
- Claims can drift away from the source passages or analysis outputs that support them.
- Citation metadata can look polished before it is actually verified.
- Data analysis and manuscript drafting are frequently disconnected.
- Revision decisions are hard to audit after several manual edits.

## What It Should Enable

- Upload local sources and produce traceable project artifacts.
- Build a local knowledge/evidence index.
- Retrieve source passages with score and provenance context.
- Draft text from allowed local evidence only.
- Audit claims, citations, safety risks, figures, and reviewer issues.
- Require human approval before applying revision patches.
- Export source, evidence, manuscript, and trust-report packages.

## What It Does Not Solve

- It does not replace real experiments.
- It does not verify scientific truth by itself.
- It does not create valid DOI values, references, p-values, or conclusions.
- It does not bypass human citation checks, statistical review, peer review, or publication decisions.
- It does not claim production readiness, compliance readiness, or peer review readiness.

## Current Focus

`v3.0.0-rc1` focuses on repository trust: clear GitHub presentation, version consistency, local verification, release packaging, static secret checks, and an honest command-center narrative. Later releases should deepen the agent loop and offline RAG quality without removing mock/offline defaults.
