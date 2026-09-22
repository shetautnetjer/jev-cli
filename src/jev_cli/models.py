from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

JsonValue = Any
Instructions = str | dict[str, Any] | list[Any]


class ChoiceQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["choice"] = "choice"
    instructions: Instructions
    criteria: dict[str, Any]

    @field_validator("criteria")
    @classmethod
    def validate_options(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not 2 <= len(value) <= 255:
            raise ValueError("Choice criteria must contain 2-255 options")
        return value


class NoulCriteria(BaseModel):
    model_config = ConfigDict(extra="forbid")
    true: Any | None = None
    false: Any | None = None


class NoulQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["noul"] = "noul"
    instructions: Instructions
    criteria: NoulCriteria | None = None


class ScoreQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["score"] = "score"
    instructions: Instructions
    criteria: list[Any]

    @field_validator("criteria")
    @classmethod
    def validate_levels(cls, value: list[Any]) -> list[Any]:
        if not 2 <= len(value) <= 10:
            raise ValueError("Score criteria must contain 2-10 ordered levels")
        return value


Question = Annotated[
    ChoiceQuestion | NoulQuestion | ScoreQuestion,
    Field(discriminator="type"),
]


class CompositionRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str
    operator: Literal["eq", "gte", "lte"]
    value: str | float | int | bool
    result: Any


class CompositionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rules: list[CompositionRule] = Field(default_factory=list)
    default: Any | None = None


class DecisionContract(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
    version: str
    model: str = "jev-latest"
    questions: dict[str, Question]
    composition: CompositionPolicy | None = None
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_composition_refs(self) -> DecisionContract:
        if self.composition:
            unknown = {r.question for r in self.composition.rules} - self.questions.keys()
            if unknown:
                raise ValueError(f"Composition references unknown questions: {sorted(unknown)}")
        return self


class StatePacket(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data: Any
    reference: str | None = None


class NormalizedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    type: Literal["choice", "noul", "score"]
    value: str | float
    probabilities: dict[str, float] | None = None
    confidence: float | None = None


class ProviderUsage(BaseModel):
    model_config = ConfigDict(extra="allow")
    input_tokens: int | None = None
    output_tokens: int | None = None


class ProviderResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requested_model: str
    resolved_model: str | None = None
    answers: dict[str, NormalizedAnswer]
    usage: ProviderUsage | None = None
    elapsed_ms: float | None = None


class DecisionReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["jev-cli/receipt-v1"] = "jev-cli/receipt-v1"
    contract_id: str
    contract_version: str
    contract_sha256: str
    state_sha256: str
    state_reference: str | None = None
    provider: str
    requested_model: str
    resolved_model: str | None = None
    answers: dict[str, NormalizedAnswer]
    usage: ProviderUsage | None = None
    provider_elapsed_ms: float | None = None
    composition: Any | None = None


class EvidenceFeature(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str
    value: Any
    source: str | None = None
    score: float | None = None


class BenchmarkCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    state: StatePacket
    contract: DecisionContract
    expected: Any
