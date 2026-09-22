# Prior Art and Clean-Room Policy

## TypeSafe

The CLI is built against TypeSafe's public System One / Jev API and documentation. API names and request/response field names are interoperability facts.

The official TypeSafe agent skill is MIT-licensed, but this repository's skill documentation is independently written for this project.

## `caio0452/jev_search`

The project was inspected as behavioral prior art. The inspected revision did not contain a repository-root license file, so this project copies **no source code** from it.

Useful high-level product ideas observed there include:
- directory discovery;
- chunking;
- concurrent semantic evaluation;
- incremental result output.

This repository independently chooses different defaults:
- no API key in argv;
- no universal confidence threshold;
- candidate recall and ranking are separate stages;
- Choice is used for mutually exclusive decisions rather than representing every criterion as independent Noul questions;
- optional retrieval cannot silently prune the legal decision space.

If the upstream project later publishes a license, that does not retroactively change this clean-room implementation history.
