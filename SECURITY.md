# Security Policy

ResearchAgent is a local-first research workspace. The current repository is not a hosted production service. Security work focuses on preventing secret leakage, unsafe release packaging, accidental publication of local runtime data, and misleading evidence artifacts.

## Reporting Vulnerabilities

Report security issues privately to the repository owner. Do not open a public issue with exploit details, credentials, private keys, API keys, or sensitive local paths.

## Secret Handling

- Keep `LLM_MODE=mock` unless live mode is explicitly configured locally.
- Do not commit `.env`, `.env.*`, API keys, passwords, private keys, tokens, local database files, or generated runtime data.
- Use `.env.example` for placeholders only.
- Run `python scripts/check_secrets_static.py` before publishing changes.
- Evidence and release logs must sanitize secrets and local absolute paths.

## Release Safety

- Source packages must exclude `projects/`, `dist/`, `.git/`, `.next/`, `node_modules/`, caches, test reports, Playwright reports, and `.env*`.
- `.env.example` is allowed if it contains placeholders only.
- Failed tests or dirty git status must never be presented as release-ready evidence.

## Research Integrity Safety

Security also includes avoiding misleading research output. Do not present mock/demo evidence as verified science, and do not claim production readiness, compliance readiness, peer review readiness, benchmark results, or publication acceptance.
