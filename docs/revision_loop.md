# Evidence-grounded Revision Plan

The revision plan turns claim-audit and reviewer findings into **patch suggestions**, not automatic edits.

Generated artifacts:

- `manuscript/revision_plan.json`
- `manuscript/revision_plan.md`
- `manuscript/patch_suggestions.json`

Every patch suggestion includes:

- `patch_id`
- `source_issue_id` / `claim_audit_id`
- `section`, `paragraph_index`, `sentence_index`
- `original_sentence`
- `suggested_sentence`
- `reason`
- `evidence_basis`
- `risk_level`
- `requires_human_approval`
- `status`
- `answer_support_status`

Rules:

- Unsupported claims should be removed, rewritten as limitations, or supported with verified local evidence.
- Weakly supported claims should use cautious wording.
- Supported claims may still require citation and metadata review.
- The system must not add DOI values, p-values, statistical significance, causal conclusions, or peer-review claims.
- `manuscript/draft.md` is not overwritten by revision planning.
