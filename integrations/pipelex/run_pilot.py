"""Run the example method. Mock is default; live providers must be selected explicitly."""

import argparse
import asyncio
import json
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

from function_only_runtime import boot
from jev_method import DecisionInput, DecisionOutput, bind_provider
from pipelex.pipelex import Pipelex
from pipelex.pipeline.runner import PipelexMTHDSProtocol

from jev_cli.io import load_contract
from jev_cli.models import StatePacket
from jev_cli.providers.mcp import MCPProvider
from jev_cli.providers.mock import MockProvider
from jev_cli.providers.typesafe import TypeSafeProvider


def main() -> int:
    """Run one explicitly selected provider and emit JSON without echoing failure input."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--state-file", type=Path, required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--provider", choices=["mock", "typesafe", "mcp"], default="mock")
    parser.add_argument("--mcp-config", type=Path)
    args = parser.parse_args()
    provider = None

    async def run() -> DecisionOutput:
        """Bind the chosen provider only while interpreting the typed decision method."""
        with bind_provider(provider):
            result = await PipelexMTHDSProtocol(library_dirs=[]).execute(
                mthds_contents=[Path("decision.mthds").read_text()],
                inputs={
                    "packet": {
                        "concept": "jev_workflows.DecisionInput",
                        "content": DecisionInput(contract=contract, state=state),
                    }
                },
            )
        output = result.pipe_output.main_stuff.content
        if not isinstance(output, DecisionOutput):
            raise RuntimeError("Method returned an unexpected type")
        return output

    previous = Path.cwd()
    try:
        contract = load_contract(args.contract.resolve())
        state = StatePacket(
            data=json.loads(args.state_file.read_text()),
            reference=args.reference,
        )
        if args.provider == "mcp":
            if args.mcp_config is None:
                parser.error("--mcp-config is required for the MCP provider")
            provider = MCPProvider.from_file(args.mcp_config.resolve())
        elif args.provider == "typesafe":
            provider = TypeSafeProvider()
        else:
            provider = MockProvider()
        os.chdir(Path(__file__).resolve().parent)
        with redirect_stdout(sys.stderr):
            boot()
            result = asyncio.run(run())
        print(result.model_dump_json())
        return 0
    except Exception as exc:
        # Preserve the error class without echoing private input or provider errors.
        print(json.dumps({"status": "failed", "error_class": type(exc).__name__}))
        return 1
    finally:
        close = getattr(provider, "close", None)
        if callable(close):
            close()
        Pipelex.teardown_if_needed()
        os.chdir(previous)


if __name__ == "__main__":
    raise SystemExit(main())
