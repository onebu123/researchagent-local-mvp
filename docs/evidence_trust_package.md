# Evidence Trust Package

The Evidence Trust Package is a local audit handoff artifact. It packages source-passage evidence, claim audit, reviewer issues, human-review state, revision suggestions, and audit logs using project-relative paths.

It is not a compliance certificate, peer-review certificate, citation-verification guarantee, or proof of scientific correctness.

## Generated Artifacts

- `exports/evidence_trust_package/evidence_trust_package.zip`
- `exports/evidence_trust_package/manifest.json`
- `trust/evidence_trust_report.md`

The manifest records:

- `package_type`
- `project_id`
- `generated_at`
- included `files`
- each file's `relative_path`, `artifact_kind`, `size_bytes`, and `sha256`
- `warnings`
- `exclusions`
- `limitations`

## Safety Boundaries

The package excludes runtime caches, local databases, `.env*`, `node_modules`, `.next`, and files outside the current project. It scans included text artifacts for absolute-path-like and secret-like strings and records warnings instead of presenting the package as release-ready.
