---
prompt_version: bibtex_generation_v1
purpose: Generate BibTeX drafts from verified local literature metadata.
---

Generate formal BibTeX entries only for records where metadata_status is verified and human_verified is true.
For placeholder, extracted, or unverified records, emit warnings or comment placeholders only.
Do not invent missing authors, journal, year, pages, DOI, publisher, or title.
Return a report that separates written entries from skipped records.
