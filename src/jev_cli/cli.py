from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Annotated, Any

import typer
import yaml
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from jev_cli import __version__
from jev_cli.discovery import (
    SecureTraversalUnavailableError,
    chunk_text,
    discover_file_records,
    read_discovered_text,
)
from jev_cli.engine import execute
from jev_cli.io import dump_json, load_contract, state_from_source
from jev_cli.models import (
    BenchmarkCase,
    ChoiceQuestion,
    DecisionContract,
    DecisionReceipt,
    NoulQuestion,
    ScoreQuestion,
    StatePacket,
)
from jev_cli.providers.base import ProviderAdapter
from jev_cli.providers.mock import MockProvider
from jev_cli.providers.typesafe import TypeSafeProvider
from jev_cli.retrieval.base import RetrievalAdapter
from jev_cli.retrieval.bge import BGERetriever
from jev_cli.retrieval.gliner import GLiNERExtractor
from jev_cli.retrieval.lexical import LexicalRetriever
from jev_cli.search import rank_chunks, semantic_judge
from jev_cli.secrets import resolve_typesafe_api_key

app = typer.Typer(
    name="jev",
    help="Typed Decision Contracts, search, and benchmarks for TypeSafe System One / Jev.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)


def _provider(name: str, mcp_config: Path | None = None) -> ProviderAdapter:
    if name == "typesafe":
        return TypeSafeProvider()
    if name == "mock":
        return MockProvider()
    if name == "mcp":
        from jev_cli.providers.mcp import MCPProvider

        configured = mcp_config or os.environ.get("JEV_MCP_CONFIG")
        if not configured:
            raise typer.BadParameter("MCP requires --mcp-config or JEV_MCP_CONFIG")
        try:
            return MCPProvider.from_file(Path(configured))
        except RuntimeError as exc:
            raise typer.BadParameter(str(exc)) from None
    raise typer.BadParameter("provider must be 'typesafe', 'mcp', or 'mock'")


def _close(provider: ProviderAdapter) -> None:
    close = getattr(provider, "close", None)
    if callable(close):
        close()


def _execute_cli(
    contract: DecisionContract,
    packet: StatePacket,
    provider: ProviderAdapter,
) -> DecisionReceipt:
    try:
        return execute(contract, packet, provider)
    except RuntimeError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None


def _parse_option(value: str) -> tuple[str, Any]:
    if "=" in value:
        key, description = value.split("=", 1)
        return key, description or None
    return value, None


@app.command()
def version() -> None:
    """Print the installed version."""
    typer.echo(__version__)


@app.command()
def init(
    output: Annotated[Path, typer.Argument(help="Contract YAML to create")] = Path(
        "jev-contract.yaml"
    ),
) -> None:
    """Scaffold a small Choice Decision Contract."""
    if output.exists():
        raise typer.BadParameter(f"Refusing to overwrite existing file: {output}")
    sample = {
        "id": "example.route",
        "version": "1",
        "model": "jev-latest",
        "questions": {
            "route": {
                "type": "choice",
                "instructions": "Which represented route matches the request?",
                "criteria": {
                    "inspect": "Read or inspect without changing state.",
                    "change": "A represented change is requested.",
                    "unknown_no_match": "None of the represented routes is a safe match.",
                },
            }
        },
    }
    output.write_text(yaml.safe_dump(sample, sort_keys=False), encoding="utf-8")
    typer.echo(str(output))


@app.command()
def doctor() -> None:
    """Check provider configuration and optional local-model extras without exposing secrets."""
    rows: list[tuple[str, str]] = []
    try:
        resolved = resolve_typesafe_api_key()
        rows.append(("TypeSafe credential", f"configured via {resolved.source}"))
    except RuntimeError:
        rows.append(("TypeSafe credential", "not configured"))
    rows.append(
        (
            "BGE extra",
            "available" if importlib.util.find_spec("sentence_transformers") else "not installed",
        )
    )
    rows.append(
        (
            "GLiNER extra",
            "available" if importlib.util.find_spec("gliner") else "not installed",
        )
    )
    table = Table("Check", "Status")
    for name, status in rows:
        table.add_row(name, status)
    console.print(table)


@app.command()
def ask(
    question_type: Annotated[str, typer.Argument(help="choice, noul, or score")],
    instructions: Annotated[str, typer.Option("--instructions", "-i")],
    state: Annotated[str | None, typer.Option("--state")] = None,
    state_file: Annotated[Path | None, typer.Option("--state-file")] = None,
    option: Annotated[
        list[str] | None, typer.Option("--option", help="Choice option NAME or NAME=DESCRIPTION")
    ] = None,
    level: Annotated[list[str] | None, typer.Option("--level", help="Ordered Score level")] = None,
    provider_name: Annotated[str, typer.Option("--provider")] = "typesafe",
    model: Annotated[str, typer.Option("--model")] = "jev-latest",
) -> None:
    """Execute one ad-hoc typed question."""
    qtype = question_type.lower()
    if qtype == "choice":
        criteria = dict(_parse_option(item) for item in (option or []))
        question: Any = ChoiceQuestion(instructions=instructions, criteria=criteria)
    elif qtype == "noul":
        question = NoulQuestion(instructions=instructions)
    elif qtype == "score":
        question = ScoreQuestion(instructions=instructions, criteria=level or [])
    else:
        raise typer.BadParameter("question_type must be choice, noul, or score")

    contract = DecisionContract(
        id="jev-cli.ask",
        version="1",
        model=model,
        questions={"answer": question},
    )
    packet = state_from_source(state_text=state, state_file=state_file)
    provider = _provider(provider_name)
    try:
        receipt = _execute_cli(contract, packet, provider)
    finally:
        _close(provider)
    typer.echo(dump_json(receipt))


@app.command("run")
def run_contract(
    contract_path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    state: Annotated[str | None, typer.Option("--state")] = None,
    state_file: Annotated[Path | None, typer.Option("--state-file")] = None,
    reference: Annotated[str | None, typer.Option("--reference")] = None,
    provider_name: Annotated[str, typer.Option("--provider")] = "typesafe",
    receipt_file: Annotated[Path | None, typer.Option("--receipt-file")] = None,
) -> None:
    """Run a saved Decision Contract."""
    contract = load_contract(contract_path)
    packet = state_from_source(state_text=state, state_file=state_file, reference=reference)
    provider = _provider(provider_name)
    try:
        receipt = _execute_cli(contract, packet, provider)
    finally:
        _close(provider)
    rendered = dump_json(receipt)
    if receipt_file:
        receipt_file.write_text(rendered + "\n", encoding="utf-8")
    typer.echo(rendered)


@app.command()
def batch(
    contract_path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    input_path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    provider_name: Annotated[str, typer.Option("--provider")] = "typesafe",
) -> None:
    """Run a contract over JSONL states, emitting one receipt per line."""
    contract = load_contract(contract_path)
    provider = _provider(provider_name)
    try:
        for line_no, line in enumerate(input_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            raw = json.loads(line)
            packet = (
                StatePacket.model_validate(raw)
                if isinstance(raw, dict) and "data" in raw
                else StatePacket(data=raw, reference=f"{input_path}:{line_no}")
            )
            typer.echo(json.dumps(_execute_cli(contract, packet, provider).model_dump(mode="json")))
    finally:
        _close(provider)


@app.command()
def search(
    query: Annotated[str, typer.Argument()],
    inputs: Annotated[list[str], typer.Argument(help="Files, directories, or globs")],
    retriever_name: Annotated[str, typer.Option("--retriever")] = "lexical",
    semantic: Annotated[bool, typer.Option("--semantic/--no-semantic")] = False,
    semantic_limit: Annotated[int | None, typer.Option("--semantic-limit", min=1)] = None,
    provider_name: Annotated[str, typer.Option("--provider")] = "typesafe",
    top: Annotated[int, typer.Option("--top", min=1)] = 10,
    chunk_lines: Annotated[int, typer.Option("--chunk-lines", min=1)] = 80,
    overlap: Annotated[int, typer.Option("--overlap", min=0)] = 10,
    no_gitignore: Annotated[bool, typer.Option("--no-gitignore")] = False,
    gliner_label: Annotated[list[str] | None, typer.Option("--gliner-label")] = None,
) -> None:
    """Recall and rank text chunks; optionally ask Jev to judge an explicit candidate pool."""
    try:
        files = discover_file_records(inputs, respect_gitignore=not no_gitignore)
    except SecureTraversalUnavailableError as exc:
        # The message quotes the user's path, which may contain "[" markup characters.
        err_console.print(f"[red]Error:[/red] {escape(str(exc))}")
        raise typer.Exit(1) from None
    chunks = []
    for discovered in files:
        text = read_discovered_text(discovered)
        if text is not None:
            chunks.extend(
                chunk_text(
                    discovered.path,
                    text,
                    lines=chunk_lines,
                    overlap=overlap,
                )
            )

    retriever: RetrievalAdapter
    if retriever_name == "lexical":
        retriever = LexicalRetriever()
    elif retriever_name == "bge":
        retriever = BGERetriever()
    else:
        raise typer.BadParameter("retriever must be lexical or bge")

    hits = rank_chunks(query, chunks, retriever)

    if semantic:
        if semantic_limit is None:
            raise typer.BadParameter(
                "--semantic requires explicit --semantic-limit so candidate pruning/cost is visible"
            )
        candidate_hits = hits[:semantic_limit]
        provider = _provider(provider_name)
        try:
            try:
                hits = semantic_judge(query, candidate_hits, provider)
            except RuntimeError as exc:
                err_console.print(f"[red]Error:[/red] {exc}")
                raise typer.Exit(1) from None
        finally:
            _close(provider)

    if gliner_label:
        extractor = GLiNERExtractor()
        for hit in hits[:top]:
            hit.features = extractor.extract(hit.chunk.text, gliner_label)

    payload = {
        "query": query,
        "files_discovered": len(files),
        "chunks_considered": len(chunks),
        "retriever": getattr(retriever, "name", retriever_name),
        "retriever_model": getattr(retriever, "model_id", None),
        "semantic_pool": semantic_limit if semantic else None,
        "hits": [hit.as_dict() for hit in hits[:top]],
    }
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


@app.command()
def bench(
    cases_path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    provider_name: Annotated[str, typer.Option("--provider")] = "mock",
) -> None:
    """Run frozen JSONL benchmark cases and compare deterministic compositions."""
    cases: list[BenchmarkCase] = []
    for line in cases_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(BenchmarkCase.model_validate_json(line))

    provider = _provider(provider_name)
    rows = []
    try:
        for case in cases:
            receipt = _execute_cli(case.contract, case.state, provider)
            rows.append(
                {
                    "id": case.id,
                    "expected": case.expected,
                    "actual": receipt.composition,
                    "passed": receipt.composition == case.expected,
                    "receipt": receipt.model_dump(mode="json", exclude_none=True),
                }
            )
    finally:
        _close(provider)
    passed = sum(bool(row["passed"]) for row in rows)
    typer.echo(
        json.dumps(
            {"cases": len(rows), "passed": passed, "failed": len(rows) - passed, "rows": rows},
            indent=2,
            ensure_ascii=False,
        )
    )


@app.command()
def cookbook() -> None:
    """List bundled public cookbook recipes."""
    recipes = [
        ("informed-decision-packet", "cookbook/informed-decision-packet.md"),
        ("decision-basis-routing", "cookbook/decision-basis-routing.md"),
        ("choice-routing", "cookbook/choice-routing.md"),
        ("function-routing", "cookbook/function-routing.md"),
        ("parallel-questions", "cookbook/parallel-questions.md"),
        ("sde-presence-cascade", "cookbook/sde-presence-cascade.md"),
        ("question-design-checklist", "cookbook/question-design-checklist.md"),
        ("search-recall", "cookbook/search-recall.md"),
        ("memory-retrieval", "cookbook/memory-retrieval.md"),
        ("unknown-no-match", "cookbook/unknown-no-match.md"),
        ("compact-reasoner", "cookbook/compact-reasoner.md"),
        ("anti-patterns", "cookbook/anti-patterns.md"),
    ]
    table = Table("Recipe", "Repository path")
    for name, path in recipes:
        table.add_row(name, path)
    console.print(table)


catalog_app = typer.Typer(help="Local SQLite question contracts and observed outcomes.")
app.add_typer(catalog_app, name="catalog")


@catalog_app.command("run")
def catalog_run(
    contract_id: str,
    version: str,
    run_id: Annotated[str, typer.Option("--run-id")],
    step_id: Annotated[str, typer.Option("--step-id")],
    db: Annotated[Path, typer.Option("--db")] = Path("jev-catalog.sqlite"),
    state: Annotated[str | None, typer.Option("--state")] = None,
    state_file: Annotated[Path | None, typer.Option("--state-file")] = None,
    reference: Annotated[str | None, typer.Option("--reference")] = None,
    provider_name: Annotated[str, typer.Option("--provider")] = "typesafe",
    mcp_config: Annotated[Path | None, typer.Option("--mcp-config")] = None,
) -> None:
    """Run an imported contract and retain its decision; no effect or success is assumed."""
    import sqlite3
    from contextlib import closing

    from jev_cli.catalog import connect, run_contract

    if mcp_config and provider_name != "mcp":
        raise typer.BadParameter("--mcp-config requires --provider mcp")
    provider = _provider(provider_name, mcp_config)
    try:
        packet = state_from_source(state_text=state, state_file=state_file, reference=reference)
        with closing(connect(db)) as store:
            receipt = run_contract(
                store,
                contract_id,
                version,
                packet,
                provider,
                run_id=run_id,
                step_id=step_id,
            )
    except sqlite3.Error:
        err_console.print(
            "[red]Error:[/red] Catalog database operation failed; "
            "inspect the run/step before retrying"
        )
        raise typer.Exit(1) from None
    except (ValueError, RuntimeError) as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None
    finally:
        _close(provider)
    typer.echo(dump_json(receipt))


@catalog_app.command("decisions")
def catalog_decisions(
    run_id: str,
    db: Annotated[Path, typer.Option("--db")] = Path("jev-catalog.sqlite"),
) -> None:
    """Read retained decisions, including pending/failed attempts, without calling Jev."""
    from contextlib import closing

    from jev_cli.catalog import connect, list_decisions

    with closing(connect(db)) as store:
        typer.echo(dump_json(list_decisions(store, run_id)))


@catalog_app.command("observe")
def catalog_observe(
    run_id: str,
    step_id: str,
    observed_result: Annotated[str, typer.Option("--result")],
    db: Annotated[Path, typer.Option("--db")] = Path("jev-catalog.sqlite"),
    effect_receipt_ref: Annotated[str | None, typer.Option("--effect-ref")] = None,
) -> None:
    """Attach one caller-observed outcome to a completed decision; does not verify the claim."""
    import sqlite3
    from contextlib import closing

    from jev_cli.catalog import connect, observe_decision

    try:
        with closing(connect(db)) as store:
            observe_decision(
                store,
                run_id,
                step_id,
                observed_result=observed_result,
                effect_receipt_ref=effect_receipt_ref,
            )
    except sqlite3.Error:
        raise typer.BadParameter(
            "Catalog database operation failed; inspect the run/step before retrying"
        ) from None
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from None
    typer.echo("recorded")


@catalog_app.command("find")
def catalog_find(
    text: str,
    db: Annotated[Path, typer.Option("--db")] = Path("jev-catalog.sqlite"),
    scope: Annotated[str | None, typer.Option("--scope")] = None,
) -> None:
    """Find contracts by literal text in IDs, questions, options or tags; no top-k cutoff."""
    from contextlib import closing

    from jev_cli.catalog import connect, find_contracts

    with closing(connect(db)) as store:
        try:
            typer.echo(dump_json(find_contracts(store, text, scope=scope)))
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from None


@catalog_app.command("import")
def catalog_import(
    contract_file: Path,
    db: Annotated[Path, typer.Option("--db")] = Path("jev-catalog.sqlite"),
    scope: Annotated[str, typer.Option("--scope")] = "general",
) -> None:
    """Import an existing versioned Decision Contract without calling a provider."""
    import sqlite3
    from contextlib import closing

    from jev_cli.catalog import connect, import_contract

    try:
        with closing(connect(db)) as store:
            digest = import_contract(
                store, load_contract(contract_file), scope=scope, source_ref=str(contract_file)
            )
    except sqlite3.Error:
        raise typer.BadParameter(
            "Catalog database operation failed; inspect the contract before retrying"
        ) from None
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from None
    typer.echo(digest)


@catalog_app.command("list")
def catalog_list(
    db: Annotated[Path, typer.Option("--db")] = Path("jev-catalog.sqlite"),
) -> None:
    """List stored contract identities, versions, and fingerprints."""
    from jev_cli.catalog import connect, list_contracts

    with connect(db) as store:
        typer.echo(dump_json(list_contracts(store)))


@catalog_app.command("show")
def catalog_show(
    contract_id: str,
    version: str,
    db: Annotated[Path, typer.Option("--db")] = Path("jev-catalog.sqlite"),
) -> None:
    """Show the imported contract, including its question and answer space."""
    from jev_cli.catalog import connect, get_contract

    with connect(db) as store:
        try:
            contract = get_contract(store, contract_id, version)
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from None
        typer.echo(dump_json(contract))


@catalog_app.command("record")
def catalog_record(
    receipt_file: Path,
    run_id: Annotated[str, typer.Option("--run-id")],
    step_id: Annotated[str, typer.Option("--step-id")],
    observed_result: Annotated[str, typer.Option("--result")],
    db: Annotated[Path, typer.Option("--db")] = Path("jev-catalog.sqlite"),
    effect_receipt_ref: Annotated[str | None, typer.Option("--effect-ref")] = None,
) -> None:
    """Record a Jev answer with a separately observed outcome; no effects are executed."""
    import sqlite3
    from contextlib import closing

    from pydantic import ValidationError

    from jev_cli.catalog import connect, record_outcome

    # Never echo parser or validation text here: it quotes the receipt's contents.
    try:
        raw_receipt = receipt_file.read_text(encoding="utf-8")
    except OSError:
        raise typer.BadParameter(f"Receipt file cannot be read: {receipt_file}") from None
    except UnicodeDecodeError:
        raise typer.BadParameter("Receipt file is not valid UTF-8 text") from None
    try:
        receipt = DecisionReceipt.model_validate_json(raw_receipt)
    except ValidationError:
        raise typer.BadParameter("Receipt file is not a valid Jev decision receipt") from None

    try:
        store = connect(db)
    except sqlite3.Error:
        raise typer.BadParameter(f"Catalog database cannot be opened: {db}") from None
    with closing(store):
        try:
            record_outcome(
                store,
                receipt,
                run_id=run_id,
                step_id=step_id,
                observed_result=observed_result,
                provider_receipt_ref=str(receipt_file),
                effect_receipt_ref=effect_receipt_ref,
            )
        except ValidationError:
            # A retained decision row failed validation; its text would quote stored receipt data.
            raise typer.BadParameter("Retained decision receipt is not valid") from None
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from None
        except sqlite3.IntegrityError as exc:
            code = getattr(exc, "sqlite_errorname", None)
            if code == "SQLITE_CONSTRAINT_FOREIGNKEY":
                message = "Receipt names a question that is not in the imported contract"
            elif code in {"SQLITE_CONSTRAINT_UNIQUE", "SQLITE_CONSTRAINT_PRIMARYKEY"}:
                message = "Outcome already recorded; existing evidence was not overwritten"
            else:
                message = "Outcome violates a catalog constraint; nothing was recorded"
            raise typer.BadParameter(message) from None
        except sqlite3.Error:
            raise typer.BadParameter(
                "Catalog database operation failed; inspect the run/step before retrying"
            ) from None
    typer.echo("recorded")


@catalog_app.command("outcomes")
def catalog_outcomes(
    run_id: str,
    db: Annotated[Path, typer.Option("--db")] = Path("jev-catalog.sqlite"),
) -> None:
    """Read exact stored answers and outcomes for one run."""
    from jev_cli.catalog import connect, list_outcomes

    with connect(db) as store:
        typer.echo(dump_json(list_outcomes(store, run_id)))


if __name__ == "__main__":
    app()
