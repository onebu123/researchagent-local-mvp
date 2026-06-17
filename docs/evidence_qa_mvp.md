# Evidence Q&A MVP

ResearchAgent Evidence Q&A is a local-first Literature RAG workflow:

`local literature files -> parsed text -> local RAG chunks -> retrieval -> answer + source_passages + support status`

It is designed to answer only from local project artifacts. It does not browse the web, call external embedding APIs, verify citations automatically, or certify that a statement is scientifically true.

## Support Status

Every RAG answer records `answer_support_status`:

| Status | Meaning |
| --- | --- |
| `supported` | At least one retrieved local passage has a strong retrieval score and does not carry low-quality or unverified-source warnings. |
| `weakly_supported` | Local passages matched, but metadata, parser quality, or verification status limits confidence. This is common for demo or placeholder literature. |
| `unsupported` | The local literature index does not contain enough passage support for the question. |

`unsupported` is not a system failure. It is a research-integrity guardrail that prevents the app from turning weak or missing local evidence into a confident research claim.

## Local Retrieval Modes

Supported retrieval modes:

- `local_keyword`: token-overlap retrieval.
- `local_hybrid`: keyword, character n-gram, metadata trust, and chunk-quality retrieval.
- `local_fts`: project-local SQLite FTS5/BM25-style retrieval.
- `local_hybrid_fts`: local hybrid retrieval blended with the SQLite FTS signal.

The SQLite index is stored as a project artifact at `literature/rag/literature_fts.sqlite3`. It is generated from local RAG chunks and does not require a global database migration, external network access, or an embedding API.

FTS/BM25 scores are retrieval signals only. They are not scientific evidence strength, citation verification, statistical review, or peer review.

## Source Passage Metadata

Returned `source_passages` keep existing fields and may include:

- `retrieval_mode`
- `fts_score`
- `bm25_score`
- `score_breakdown`
- `position_label`
- `metadata_trust_level`
- `parser_quality_label`
- `parser_quality_score`
- `evidence_warning_flags`

Warning flags such as `placeholder_metadata`, `unverified_metadata`, `low_parser_quality`, `failed_or_empty_parse`, `short_chunk`, and `low_lexical_diversity` are surfaced so users can see why a passage should not be treated as verified evidence.

## Offline Evaluation

Run a local eval with:

```bash
python scripts/evaluate_rag.py --retrieval-mode local_hybrid_fts --output /tmp/researchagent_rag_eval_report.json
```

The eval runner accepts JSONL cases:

```json
{"question":"...","expected_answer_support_status":"supported|weakly_supported|unsupported","expected_terms":["..."],"must_not_contain":["statistically significant","causal","p-value"]}
```

The report includes support-status accuracy, unsupported refusal rate, source-passage rate, and failures. These are local regression checks, not external benchmark claims.

## Non-Goals

- Not a paper-writing service.
- Not a citation verification guarantee.
- Not a peer-review replacement.
- Not a statistical-review certificate.
- Not a production search benchmark.
- Not a source of fabricated DOI values, authors, years, journals, pages, p-values, significance claims, causal conclusions, or verified references.

## Page-aware Source Locators

RAG chunks now carry position metadata when available:

- `page_start`
- `page_end`
- `page_quality_signals`
- `position_label`
- `source_locator`

For PDFs, page locators come from the local parser's best-effort page records. For text and Markdown files, the locator falls back to a character range. These locators help auditability, but low-quality parser output must still be reviewed by a human before citation.

## Answer Contract

RAG answers are post-validated after mock or live LLM synthesis. Unsupported answers are replaced with a safe unsupported response if they contain strong statistical, causal, proof, or p-value wording. Weakly supported answers must stay cautious and preserve limitations.

Live LLM mode, when configured, is a synthesis layer over retrieved source passages. It is not an evidence source.

## Related Workflows

- [Draft Claim Audit](draft_claim_audit.md)
- [Human Review Queue](human_review_queue.md)
- [Evidence-grounded Revision Plan](revision_loop.md)
- [Evidence Trust Package](evidence_trust_package.md)
- [Local Evaluation](evaluation.md)
