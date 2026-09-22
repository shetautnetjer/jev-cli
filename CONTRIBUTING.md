# Contributing

Thanks for improving `jev-cli`.

## Development

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run mypy src/jev_cli
```

Keep changes narrow and add tests for observable behavior.

## Decision Contract changes

If you change contract semantics, question validation, receipt fields, or search pruning:
- update the architecture/cookbook;
- add a regression test;
- preserve explicit unknown/no-match handling where candidate coverage may be incomplete;
- do not turn model confidence into execution authority.

## Security

Never commit API keys, bearer tokens, cookies, private endpoints, private hostnames, or personal filesystem paths.

Run `python scripts/verify_jev_cli_publication.py` before opening a release PR.
