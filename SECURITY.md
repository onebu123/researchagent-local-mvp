# Security Policy

ResearchAgent is a local-first research workspace. Please do not commit secrets, API keys, private keys, passwords, local machine paths, or generated runtime data.

## Reporting Vulnerabilities

Report security issues privately to the repository owner. Do not open a public issue with exploit details, credentials, or sensitive local paths.

## Secret Handling

- Keep `LLM_MODE=mock` unless live mode is explicitly configured locally.
- Keep API keys out of git and out of generated evidence logs.
- Use `.env.example` for placeholders only.
- Run `python scripts/check_secrets_static.py` before publishing changes.

## Supported Scope

The current repository is not a hosted production service. Security review focuses on preventing secret leakage, unsafe release packaging, accidental publication of local runtime data, and misleading evidence artifacts.
