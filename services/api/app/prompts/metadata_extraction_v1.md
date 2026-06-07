---
prompt_version: metadata_extraction_v1
purpose: Draft literature metadata lookup candidates without auto-verification.
---

Use only provider-returned metadata or existing local metadata.
Do not invent DOI, authors, journal, year, pages, or venue.
Mark all candidates as needs_human_review unless a human has explicitly verified them.
Do not modify literature_index.json.
Return JSON with provider, literature_id, candidates, warnings, and human_verification_required.
