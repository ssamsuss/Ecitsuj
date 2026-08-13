import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, Numeric, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

class Case(Base):
    __tablename__ = "cases"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    jurisdiction: Mapped[str | None] = mapped_column(String(50))
    charge: Mapped[str | None] = mapped_column(Text)
    standard_of_proof: Mapped[str] = mapped_column(Text, default="beyond a reasonable doubt")
    facts_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    instructions_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    evidence_items = relationship("EvidenceItem", back_populates="case", cascade="all, delete-orphan")
    runs = relationship("SimulationRun", back_populates="case", cascade="all, delete-orphan")

class EvidenceItem(Base):
    __tablename__ = "evidence_items"
    __table_args__ = (
        UniqueConstraint("case_id", "evidence_code", name="uq_evidence_items_case_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"))
    evidence_code: Mapped[str] = mapped_column(String(20), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    case = relationship("Case", back_populates="evidence_items")

class SimulationRun(Base):
    __tablename__ = "simulation_runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"))
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    temperature: Mapped[float] = mapped_column(Numeric(3,2), default=0.4)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 4))

    case = relationship("Case", back_populates="runs")
    jurors = relationship("Juror", back_populates="run", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="run", cascade="all, delete-orphan")
    messages = relationship("DeliberationMessage", back_populates="run", cascade="all, delete-orphan")
    metrics = relationship("RunMetric", back_populates="run", uselist=False, cascade="all, delete-orphan")

class Juror(Base):
    __tablename__ = "jurors"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulation_runs.id", ondelete="CASCADE"))
    juror_number: Mapped[int] = mapped_column(Integer, nullable=False)
    persona_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    run = relationship("SimulationRun", back_populates="jurors")
    votes = relationship("Vote", back_populates="juror")

class Vote(Base):
    __tablename__ = "votes"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulation_runs.id", ondelete="CASCADE"))
    juror_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jurors.id", ondelete="CASCADE"))
    phase: Mapped[str] = mapped_column(String(20), nullable=False)  # initial|final|temp
    verdict: Mapped[str] = mapped_column(String(20), nullable=False)  # guilty|not_guilty|undecided
    confidence: Mapped[float] = mapped_column(Numeric(4,3), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    cited_evidence_codes: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    what_changed: Mapped[str | None] = mapped_column(Text)  # final-phase only
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run = relationship("SimulationRun", back_populates="votes")
    juror = relationship("Juror", back_populates="votes")

class DeliberationMessage(Base):
    __tablename__ = "deliberation_messages"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulation_runs.id", ondelete="CASCADE"))
    round_no: Mapped[int] = mapped_column(Integer, nullable=False)
    turn_no: Mapped[int] = mapped_column(Integer, nullable=False)
    juror_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jurors.id", ondelete="CASCADE"))
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    cited_evidence_codes: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    stance: Mapped[str | None] = mapped_column(String(20))  # support|challenge|clarify
    flags_json: Mapped[dict] = mapped_column(JSON, default=dict)

    run = relationship("SimulationRun", back_populates="messages")

class RunMetric(Base):
    __tablename__ = "run_metrics"
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulation_runs.id", ondelete="CASCADE"), primary_key=True)
    initial_split_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    final_split_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    vote_entropy_initial: Mapped[float | None] = mapped_column(Numeric(6,4))
    vote_entropy_final: Mapped[float | None] = mapped_column(Numeric(6,4))
    persuasion_index: Mapped[float | None] = mapped_column(Numeric(6,4))
    citation_coverage: Mapped[float | None] = mapped_column(Numeric(6,4))
    contradiction_rate: Mapped[float | None] = mapped_column(Numeric(6,4))
    dominance_index: Mapped[float | None] = mapped_column(Numeric(6,4))
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run = relationship("SimulationRun", back_populates="metrics")