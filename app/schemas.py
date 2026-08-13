from pydantic import BaseModel, Field, model_validator
from typing import Annotated, Literal, Any
from uuid import UUID

Verdict = Literal["guilty", "not_guilty", "undecided"]
VotePhase = Literal["initial", "temp", "final"]
EvidenceCode = Annotated[str, Field(pattern=r"^E[0-9]+$")]

class EvidenceItemIn(BaseModel):
    model_config = {"extra": "forbid"}

    code: str = Field(min_length=2, pattern=r"^E[0-9]+$")
    kind: str = Field(min_length=1)
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

class CasePacketIn(BaseModel):
    model_config = {"extra": "forbid"}

    title: str = Field(min_length=1)
    jurisdiction: str | None = None
    charge: str | None = None
    standard_of_proof: str = Field(default="beyond a reasonable doubt", min_length=1)
    facts: list[Annotated[str, Field(min_length=1)]] = Field(min_length=1)
    jury_instructions: str = Field(min_length=1)
    evidence_items: list[EvidenceItemIn] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_evidence_codes(self):
        codes = [item.code for item in self.evidence_items]
        if len(codes) != len(set(codes)):
            raise ValueError("evidence codes must be unique")
        return self

class CaseOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    title: str

class EvidenceIndexEntryOut(BaseModel):
    code: EvidenceCode
    kind: str
    content: str
    tags: list[str] = Field(default_factory=list)

class RunCreateIn(BaseModel):
    case_id: UUID
    model_name: str = "gpt-4.1"
    temperature: float = 0.4
    max_rounds: int = 4
    juror_count: int = 12
    seed: int = 42
    timeout_seconds: int | None = None

class VoteOut(BaseModel):
    juror_number: int
    phase: VotePhase
    verdict: Verdict
    confidence: float
    rationale: str
    cited_evidence_codes: list[EvidenceCode] = Field(default_factory=list)
    what_changed: str | None = None

class DeliberationTurnOut(BaseModel):
    round_no: int
    turn_no: int
    juror_number: int
    message: str
    cited_evidence_codes: list[str]
    flags: dict[str, Any] = Field(default_factory=dict)

class RunReportOut(BaseModel):
    run_id: UUID
    status: str
    initial_split: dict[str, int]
    final_split: dict[str, int]
    vote_shifts: list[dict[str, Any]]
    warnings: list[str] = Field(default_factory=list)
    metrics: dict[str, Any]

class InitialVoteResult(BaseModel):
    model_config = {"extra": "forbid"}

    verdict: Verdict
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1, max_length=1200)
    cited_evidence_codes: list[EvidenceCode] = Field(default_factory=list)

class DeliberationTurnResult(BaseModel):
    model_config = {"extra": "forbid"}

    message: str = Field(min_length=1, max_length=1000)
    cited_evidence_codes: list[EvidenceCode] = Field(default_factory=list)
    stance: Literal["support", "challenge", "clarify"]

class FinalVoteResult(InitialVoteResult):
    what_changed: str = Field(min_length=1, max_length=800)