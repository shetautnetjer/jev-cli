# Security

`jev-cli` is designed for use in developer terminals, CI, containers, and agent runtimes where command history and logs may be retained.

## Credentials

Raw API keys are never accepted as command-line arguments.

Supported sources:
- `TYPESAFE_API_KEY`
- `TYPESAFE_API_KEY_FILE`
- `/run/secrets/typesafe_api_key` when present

The CLI reports **where** a credential was resolved from, never its value. Authorization headers are never rendered in normal or debug output.

Do not bake credentials into Docker images, Compose files, examples, fixtures, GitHub Actions variables in source, or Git history.

## State and receipts

Raw input state can contain source code, prompts, personal data, or proprietary text. Receipts therefore store a SHA-256 state digest and optional caller-supplied reference by default, not the raw state.

Any future raw-state persistence must be explicit opt-in and clearly separated from the default receipt path.

## Search

Directory traversal follows explicit roots and configurable ignore rules. Directory scans reject file symlinks, require resolved candidates to remain inside the selected root, and reopen discovered files descriptor-relative with no-follow semantics for every path component.

Symlinked `.gitignore` files are ignored rather than followed. Glob-expanded file symlinks are rejected.

A caller may still explicitly select a literal symlink as a direct file input. That is treated as an intentional explicit path choice rather than implicit directory/glob traversal.

The CLI does not execute scanned files.

Semantic models are advisory. Their probabilities do not grant permission to act on files or external systems.

## Publication checks

Before release:
- run tests, type/lint checks, and Docker build;
- scan current files and Git history for secret-like material;
- scan for local-machine paths and private identifiers;
- inspect dependencies and licenses;
- verify prior-art source was not copied;
- fresh-clone and rerun documented tests.
