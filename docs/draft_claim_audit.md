# Draft Claim Audit

Draft Claim Audit checks manuscript-like sentences against the local Literature RAG index. It is designed for one practical question: **does the project-local evidence support this claim, weakly mention it, or fail to support it?**

It is not peer review, not automatic citation verification, and not a paper-writing service.

## Workflow

1. Read a manuscript draft from `manuscript/draft.md` or a request payload.
2. Extract claim-like sentences from Abstract, Results, Discussion, and Conclusion sections.
3. Ask local Literature RAG about each sentence.
4. Save `provenance/claim_audit.json` and `provenance/claim_audit.md`.
5. Keep unsupported and weakly supported claims visible for human review.

## Claim Audit Item Fields

Each `claim_audit` item includes:

- `claim_audit_id`
- `section`, `paragraph_index`, `sentence_index`
- `sentence`
- `answer_support_status`: `supported`, `weakly_supported`, or `unsupported`
- `matched_source_passages`
- `unsupported_notes`
- `evidence_warning_flags`
- `recommended_action`
- `human_review_required`
- `rag_answer_id`
- `retrieval_mode`
- `top_source_score`

`recommended_action` is intentionally conservative:

- `keep_with_citation`: local passage support exists, but final citation still needs human review.
- `rewrite_as_limitation`: support is weak or metadata/parser quality is limited.
- `add_source_or_remove`: local passages do not support the claim.
- `needs_human_review`: evidence exists but warnings remain.

Strong statistical, causal, proof, or p-value wording is downgraded unless local evidence clearly supports it. The system must not invent p-values, DOI values, verified references, or causal conclusions.
