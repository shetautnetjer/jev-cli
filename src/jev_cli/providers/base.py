from __future__ import annotations

from typing import Protocol

from jev_cli.models import DecisionContract, ProviderResult, StatePacket


class ProviderAdapter(Protocol):
    name: str

    def evaluate(self, contract: DecisionContract, state: StatePacket) -> ProviderResult: ...
