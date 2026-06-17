# Human Review Queue

The Human Review Queue aggregates local risk signals into one review list. It helps a human decide what needs verification, rewriting, approval, or dismissal before any external use.

It does **not** verify scientific truth. A local approval is not peer review, citation verification, compliance certification, or publication readiness.

## Sources

The queue can include items from:

- placeholder or unverified literature metadata
- low-quality PDF parsing
- unsupported or weakly supported claim audit results
- reviewer major issues
- revision patch suggestions that require human approval

Queue artifacts:

- `trust/human_review_queue.json`
- `trust/human_review_decisions.jsonl`

## Item Fields

Each item includes:

- `review_id`
- `review_type`
- `severity`: `blocking`, `warning`, or `info`
- `title`
- `description`
- `artifact_path`
- `entity_type`
- `entity_id`
- `recommended_action`
- `status`
- `created_at`
- `decided_at`
- `decision_reason`
- `human_review_required`

A decision records local human intent and appends an audit event. It does not convert an unverified claim into a verified scientific result.
