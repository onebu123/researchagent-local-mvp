# Local Evaluation

ResearchAgent includes local regression evals for Evidence Q&A and Draft Claim Audit. These evals use small demo fixtures and are not external benchmarks.

## Commands

```bash
python scripts/evaluate_rag.py --retrieval-mode local_hybrid_fts --output /tmp/researchagent_rag_eval.json
python scripts/evaluate_claim_audit.py --retrieval-mode local_hybrid_fts --output /tmp/researchagent_claim_eval.json
python scripts/evaluate_local_researchagent.py --output /tmp/researchagent_local_eval.json
```

## Metrics

RAG eval reports:

- `support_status_accuracy`
- `unsupported_refusal_rate`
- `answer_has_source_passage_rate`
- `failures`

Claim audit eval reports:

- `support_status_accuracy`
- `unsupported_claim_detection_rate`
- `unsafe_wording_rate`
- `failures`

`unsupported` is a successful integrity outcome when the local evidence is insufficient.

## Fixture Policy

Fixtures under `evals/local_evidence_qa/` are demo text, not real papers. Do not describe their scores as external leaderboard results or evidence of general scientific correctness.
