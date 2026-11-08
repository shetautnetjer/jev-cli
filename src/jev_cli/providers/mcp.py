"""Optional stdio client for the jev_capabilities/jev_evaluate MCP contract."""

from __future__ import annotations

import asyncio
import math
import os
import re
from datetime import timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from jev_cli.models import (
    DecisionContract,
    ProviderResult,
    StatePacket,
)
from jev_cli.providers.validation import normalize_answers, normalize_usage


class MCPConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)
    command: str = Field(min_length=1)
    args: list[str] = Field(default_factory=list)
    project_id: str = Field(min_length=1)
    timeout_seconds: float = Field(default=60, gt=0, le=120)


def _safe_label(value: Any) -> str | None:
    """Keep only bounded identifiers accepted by the receipt metadata format."""
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:/-]{1,128}", value):
        return value
    return None


def normalize(
    body: dict[str, Any],
    contract: DecisionContract,
    project_id: str,
    capabilities: dict[str, Any] | None = None,
) -> ProviderResult:
    """Reject partial/mismatched answers; retain only selected routing metadata."""
    try:
        if (body["project_id"], body["contract_id"], body["contract_version"]) != (
            project_id,
            contract.id,
            contract.version,
        ):
            raise ValueError
        answers = normalize_answers(body["answers"], contract)
        requested = _safe_label(body["requested_model"])
        resolved = _safe_label(body["resolved_model"])
        if not requested or not resolved or type(body["fallback_used"]) is not bool:
            raise ValueError
        providers = (capabilities or {}).get("providers")
        if not isinstance(providers, dict):
            raise ValueError
        route = providers.get("fallback" if body["fallback_used"] else "primary")
        if (
            not isinstance(route, dict)
            or route.get("enabled") is not True
            or not _safe_label(route.get("id"))
            or body.get("provider") != route.get("id")
            or requested != route.get("model")
        ):
            raise ValueError
        if not body["fallback_used"]:
            primary_model = (capabilities or {}).get("model", contract.model)
            if primary_model != "jev-latest" and requested != primary_model:
                raise ValueError
            if contract.model != "jev-latest" and resolved != contract.model:
                raise ValueError
            if requested != resolved:
                raise ValueError
        else:
            # The service permits a versioned OpenRouter resolution of its
            # configured alias. Keep both identities intact in the receipt.
            if not (resolved == requested or resolved.startswith(requested + "-")):
                raise ValueError
        usage = normalize_usage(body.get("usage"))
        elapsed = body.get("elapsed_ms")
        if (
            isinstance(elapsed, bool)
            or not isinstance(elapsed, (int, float))
            or not math.isfinite(elapsed)
            or elapsed < 0
        ):
            raise ValueError
        metadata = {
            "request_id": _safe_label(body.get("request_id")),
            "service_provider": _safe_label(body.get("provider")),
            "project_id": project_id,
            "fallback_used": body["fallback_used"],
            "fallback_reason": _safe_label(body.get("fallback_reason")),
            "provider_attempts": [
                {
                    "provider": _safe_label(a.get("provider")),
                    "status": _safe_label(a.get("status")),
                    "error_code": _safe_label((a.get("error") or {}).get("code")),
                }
                for a in body.get("provider_attempts", [])
            ],
        }
        return ProviderResult(
            requested_model=requested,
            resolved_model=resolved,
            answers=answers,
            usage=usage,
            elapsed_ms=elapsed,
            metadata=metadata,
        )
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError, RuntimeError):
        raise RuntimeError("MCP returned an invalid or mismatched Jev receipt") from None


class MCPProvider:
    name = "mcp"

    def __init__(self, config: MCPConfig) -> None:
        """Retain validated launch settings; defer subprocess startup until evaluation."""
        self.config = config

    @classmethod
    def from_file(cls, path: Path) -> MCPProvider:
        """Load strict launch settings without exposing invalid file contents in errors."""
        try:
            return cls(MCPConfig.model_validate_json(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            raise RuntimeError("Cannot read valid MCP config; see docs/INTEGRATIONS.md") from None

    def evaluate(self, contract: DecisionContract, state: StatePacket) -> ProviderResult:
        """Run one bounded MCP evaluation and hide transport details from CLI errors."""
        try:
            return asyncio.run(self._evaluate(contract, state))
        except ImportError:
            raise RuntimeError("MCP extra is required: install jev-cli[mcp]") from None
        except Exception:
            # SDK exception groups can contain request data or server stderr. Do not echo them.
            raise RuntimeError(
                "MCP evaluation failed; check configuration, model pin, and service health. "
                "No CLI retry was attempted."
            ) from None

    async def _evaluate(self, contract: DecisionContract, state: StatePacket) -> ProviderResult:
        """Negotiate a fresh stdio session and validate its single evaluation receipt.

        The configured wrapper owns credentials; the timeout covers startup and
        tool calls. Requested model pins and returned route provenance must agree.
        """
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        params = StdioServerParameters(command=self.config.command, args=self.config.args)
        async with asyncio.timeout(self.config.timeout_seconds):
            # The trusted wrapper owns credentials. Neither arguments nor raw stderr are retained.
            with open(os.devnull, "w") as errlog:
                async with stdio_client(params, errlog=errlog) as (read, write):
                    async with ClientSession(
                        read,
                        write,
                        read_timeout_seconds=timedelta(seconds=self.config.timeout_seconds),
                    ) as session:
                        await session.initialize()
                        caps = await session.call_tool("jev_capabilities", {})
                        data = caps.structuredContent
                        if caps.isError or not isinstance(data, dict):
                            raise RuntimeError("Invalid capabilities")
                        if contract.model != "jev-latest" and contract.model != data.get("model"):
                            raise RuntimeError("Contract model differs from MCP primary model")
                        request = {
                            "project_id": self.config.project_id,
                            "contract_id": contract.id,
                            "contract_version": contract.version,
                            "source_refs": [state.reference] if state.reference else [],
                            "state": state.data,
                            "questions": {
                                k: q.model_dump(mode="json", exclude_none=True)
                                for k, q in contract.questions.items()
                            },
                        }
                        response = await session.call_tool("jev_evaluate", {"request": request})
                        body = response.structuredContent
                        if (
                            response.isError
                            or not isinstance(body, dict)
                            or body.get("status") != "ok"
                        ):
                            raise RuntimeError("Jev service did not return a successful receipt")
                        return normalize(body, contract, self.config.project_id, capabilities=data)
