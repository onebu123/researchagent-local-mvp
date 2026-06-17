# Citation Binding and Compile Pipeline

ResearchAgent can now connect the Auto Scientist manuscript to two final-paper readiness layers:

1. **Paper citation/source-passage binding**: each claim-like manuscript sentence is matched to local source passages and the local approved-reference state.
2. **LaTeX/PDF compile pipeline**: the generated LaTeX source can be checked and compiled locally when a supported engine is available, or a clearly labeled preview PDF can be generated as a non-publication fallback.

These features support review and handoff. They do not certify citation correctness, scientific validity, peer review, or publication readiness.

## API

Generate paper citation bindings:

```http
POST /api/projects/{project_id}/auto-scientist/paper-citation-bindings
```

Read paper citation bindings:

```http
GET /api/projects/{project_id}/auto-scientist/paper-citation-bindings
```

Run the local LaTeX/PDF pipeline:

```http
POST /api/projects/{project_id}/auto-scientist/paper-compile
```

Read the latest compile report:

```http
GET /api/projects/{project_id}/auto-scientist/paper-compile
```

## Citation binding artifacts

The binding workflow writes:

```text
manuscript/paper_citation_bindings.json
manuscript/paper_citation_bindings.md
manuscript/latest_paper_citation_binding.json
manuscript/auto_scientist_paper_citation_bound.md
```

Each binding records:

```text
citation_binding_id
manuscript_file
section / paragraph_index / sentence_index
sentence
claim_like
binding_status
citation_support_status
matched_source_passages
formal_reference_literature_ids
suggested_citation_marker
citation_warning_flags
human_review_required
recommended_action
```

`citation_support_status` values include:

```text
formal_reference_available
source_passage_only
missing_source_passage
not_applicable
```

Formal LaTeX citation markers are emitted only for references that are approved through the local reference workflow. Otherwise the system uses source-passage markers and requires human review.

## Compile artifacts

The compile pipeline writes:

```text
manuscript/latex_compile_report.json
manuscript/latex_compile_report.md
manuscript/auto_scientist_paper.pdf                 # only if local LaTeX compilation succeeds
manuscript/auto_scientist_paper_preview.pdf         # optional fallback preview, not publication-ready
manuscript/latex_build/stdout.txt                   # when a local engine runs
manuscript/latex_build/stderr.txt                   # when a local engine runs
```

The report uses `compile_status` values such as:

```text
compiled
tool_unavailable
compile_skipped
compile_failed
compile_timeout
unsafe_latex_rejected
```

The pipeline rejects dangerous LaTeX patterns such as shell escape, `\write18`, path-traversing `\input`, and `minted`. It never treats a compiled PDF or preview PDF as scientific validation.

## Human review and trust package

Citation binding risks and compile warnings enter the Human Review Queue. Evidence Trust Package exports include the citation binding files, compile report, and generated PDF/preview PDF when present.

Review before external use:

```text
- weak or unbound citation bindings
- source-passage-only citation suggestions
- unapproved references
- generated-code experiment claims
- compile warnings or fallback preview PDFs
```

## Limitations

- The source-passage matcher is heuristic and local-only.
- Page locators depend on parser quality and may require manual review.
- A fallback preview PDF is not a LaTeX compilation and is not submission-ready.
- ResearchAgent does not verify DOI, citation metadata, p-values, causal conclusions, or peer review status automatically.
