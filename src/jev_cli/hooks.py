"""Host-triggered decision hooks over the existing versioned question catalog.

A hook returns a recommendation. It cannot execute a tool, change a model,
discard context or grant authority.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from jev_cli.catalog import run_contract
from jev_cli.engine import sha256_json
from jev_cli.models import DecisionContract, DecisionReceipt, ProviderResult, StatePacket
from jev_cli.providers.base import ProviderAdapter

Label = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,191}$")]


class HookRoute(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    contract_id: Label
    version: Label


class HookConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    routes: dict[Label, HookRoute]


class HookEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    source: Label
    id: Label
    name: Label
    state: StatePacket
    correlation: dict[Label, Label] = Field(default_factory=dict)


class _LazyProvider:
    """Reserve before opening the provider; duplicates require no credentials."""

    def __init__(self, factory: Callable[[], ProviderAdapter]) -> None:
        self.factory = factory
        self.inner: ProviderAdapter | None = None
        self.attempted = False

    name = "unavailable"

    def evaluate(self, contract: DecisionContract, state: StatePacket) -> ProviderResult:
        """Construct the provider only after reservation and mark the evaluation attempt."""
        self.attempted = True
        self.inner = self.factory()
        self.name = self.inner.name
        return self.inner.evaluate(contract, state)

    def close(self) -> None:
        """Release an initialized provider without invalidating an already retained receipt."""
        close = getattr(self.inner, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass  # A close failure cannot undo an already retained receipt.


def run_hook(
    db: sqlite3.Connection,
    config: HookConfig,
    event: HookEvent,
    provider_factory: Callable[[], ProviderAdapter],
) -> dict[str, Any]:
    """Read/replay freely; new admission requires no pending caller transaction."""
    run_id = "hook:" + sha256_json({"source": event.source, "id": event.id})
    step_id = "hook"
    route = config.routes.get(event.name)
    base: dict[str, Any] = {
        "event_id": event.id,
        "event_name": event.name,
        "run_id": run_id,
        "step_id": step_id,
        "authority_granted": False,
    }
    if route is None:
        return {**base, "status": "skipped", "reason": "no_configured_contract", "replayed": False}
    packet = StatePacket(
        data={"event": event.model_dump(exclude={"state"}), "evidence": event.state.data},
        reference=event.state.reference,
    )
    digest = sha256_json(packet.data)

    def read() -> dict[str, Any] | None:
        """Reuse only a reservation whose contract, evidence hash and reference still match."""
        row = db.execute(
            "SELECT * FROM decisions WHERE run_id=? AND step_id=?", (run_id, step_id)
        ).fetchone()
        if row is None:
            return None
        if (row["contract_id"], row["version"], row["state_digest"], row["state_reference"]) != (
            route.contract_id,
            route.version,
            digest,
            packet.reference,
        ):
            raise ValueError("Event ID already retained with different contract or evidence")
        return dict(row)

    row = read()
    replayed = row is not None
    attempted = False
    if row is None:
        if db.in_transaction:
            raise ValueError("Hook admission requires a connection without a pending transaction")
        provider = _LazyProvider(provider_factory)
        try:
            run_contract(
                db,
                route.contract_id,
                route.version,
                packet,
                provider,
                run_id=run_id,
                step_id=step_id,
            )
        except Exception:
            # Reservation is already durable when provider initialization/evaluation fails.
            # Another process can also have reserved this event since our initial read.
            if read() is None:
                raise RuntimeError("Hook admission failed; no decision was retained") from None
        finally:
            attempted = provider.attempted
            replayed = not attempted
            provider.close()
        row = read()
    if row is None:
        raise RuntimeError("Missing retained hook decision")
    receipt = (
        DecisionReceipt.model_validate_json(row["receipt_json"]) if row["receipt_json"] else None
    )
    telemetry: dict[str, Any] = {
        "event_name": "jev.hook." + row["status"],
        "event_id": event.id,
        "source": event.source,
        "hook_name": event.name,
        "run_id": run_id,
        "step_id": step_id,
        "contract_id": route.contract_id,
        "contract_version": route.version,
        "state_sha256": digest,
        "replayed": replayed,
        "authority_granted": False,
        "evaluation_attempted": attempted,
    }
    for key in ("task_id", "operation_id", "thread_id", "turn_id", "trace_id", "span_id"):
        if key in event.correlation:
            telemetry[key] = event.correlation[key]
    if receipt:
        telemetry.update(
            {
                "provider": receipt.provider,
                "resolved_model": receipt.resolved_model,
                "provider_elapsed_ms": receipt.provider_elapsed_ms if attempted else None,
                "usage": {
                    key: value
                    for key, value in receipt.usage.model_dump().items()
                    if key
                    in {
                        "input_tokens",
                        "output_tokens",
                        "cached_input_tokens",
                        "cache_write_tokens",
                        "reasoning_output_tokens",
                    }
                    and type(value) is int
                    and value >= 0
                }
                if attempted and receipt.usage
                else None,
            }
        )
    return {
        **base,
        "status": row["status"],
        "replayed": replayed,
        "receipt": receipt.model_dump(mode="json", exclude_none=True) if receipt else None,
        "error_code": row["error_code"],
        "telemetry": telemetry,
    }
