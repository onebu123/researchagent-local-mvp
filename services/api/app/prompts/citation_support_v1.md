---
prompt_version: citation_support_v1
purpose: Check whether manuscript claims are supported by local source passages.
---

Compare each claim against retrieved chunks and source passage evidence.
Use statuses supported, partial, unsupported, or needs_human_review.
Placeholder or unverified metadata cannot exceed partial without human verification.
Do not treat overlapping keywords as proof.
Return JSON with claim_id, status, matched_chunk_ids, and notes.
