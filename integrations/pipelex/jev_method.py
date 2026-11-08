"""Optional Pipelex 0.64 adapter for DecisionContract and DecisionReceipt.

The host binds the provider; method input cannot select credentials or endpoints.
No actions, memory writes, retries or implicit model calls are performed here.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from pipelex.core.memory.working_memory import WorkingMemory
from pipelex.core.stuffs.structured_content import StructuredContent
from pipelex.runtime_hub import get_class_registry
from pipelex.system.registries.func_registry import func_registry, pipe_func

from jev_cli.engine import execute
from jev_cli.models import DecisionContract, DecisionReceipt, StatePacket
from jev_cli.providers.base import ProviderAdapter

_provider: ContextVar[ProviderAdapter | None] = ContextVar("jev_pipelex_provider", default=None)


class DecisionInput(StructuredContent):
    contract: DecisionContract
    state: StatePacket


class DecisionOutput(StructuredContent):
    receipt: DecisionReceipt
    disposition: str


@contextmanager
def bind_provider(provider: ProviderAdapter) -> Iterator[None]:
    """Bind one caller-owned provider for a run, including worker-thread dispatch."""
    token = _provider.set(provider)
    try:
        yield
    finally:
        _provider.reset(token)


@pipe_func(name="jev_evaluate_contract")
def evaluate_jev(working_memory: WorkingMemory) -> DecisionOutput:
    packet = working_memory.get_stuff_as("packet", content_type=DecisionInput)
    policy = packet.contract.composition
    implicit_choice = (
        policy is None
        and len(packet.contract.questions) == 1
        and next(iter(packet.contract.questions.values())).type == "choice"
    )
    string_policy = (
        policy is not None
        and isinstance(policy.default, str)
        and all(isinstance(rule.result, str) for rule in policy.rules)
    )
    if not implicit_choice and not string_policy:
        raise ValueError("This method requires a contract with a string routing composition")
    provider = _provider.get()
    if provider is None:
        raise RuntimeError("A host must bind the Jev provider before executing the method")
    receipt = execute(packet.contract, packet.state, provider)
    if not isinstance(receipt.composition, str):
        raise ValueError("The provider result could not compose to a routing string")
    return DecisionOutput(receipt=receipt, disposition=receipt.composition)


@pipe_func(name="jev_return_decision")
def return_decision(working_memory: WorkingMemory) -> DecisionOutput:
    """Return an advisory result, preserving the exact receipt for the calling host."""
    return working_memory.get_stuff_as("decision", content_type=DecisionOutput)


@pipe_func(name="jev_needs_evidence")
def needs_evidence(working_memory: WorkingMemory) -> DecisionOutput:
    return return_decision(working_memory).model_copy(update={"disposition": "needs_evidence"})


@pipe_func(name="jev_unknown_route")
def unknown_route(working_memory: WorkingMemory) -> DecisionOutput:
    return return_decision(working_memory).model_copy(update={"disposition": "unknown_no_match"})


def register_pipelex() -> None:
    """Register only these adapter types/functions after the host boots Pipelex."""
    get_class_registry().register_classes([DecisionInput, DecisionOutput])
    for name, function in (
        ("jev_evaluate_contract", evaluate_jev),
        ("jev_return_decision", return_decision),
        ("jev_needs_evidence", needs_evidence),
        ("jev_unknown_route", unknown_route),
    ):
        func_registry.register_function(function, name=name)
