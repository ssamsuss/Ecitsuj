"""Create the initial application schema.

Revision ID: 0001_initial
Revises:
"""
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


SCHEMA_SQL = """
CREATE TABLE cases (
  id UUID PRIMARY KEY,
  title TEXT NOT NULL,
  jurisdiction TEXT,
  charge TEXT,
  standard_of_proof TEXT DEFAULT 'beyond a reasonable doubt',
  facts_json JSONB NOT NULL,
  instructions_text TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE evidence_items (
  id UUID PRIMARY KEY,
  case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
  evidence_code TEXT NOT NULL,
  kind TEXT NOT NULL,
  content TEXT NOT NULL,
  metadata_json JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE simulation_runs (
  id UUID PRIMARY KEY,
  case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
  model_name TEXT NOT NULL,
  temperature NUMERIC(3,2) DEFAULT 0.4,
  status TEXT NOT NULL,
  config_json JSONB NOT NULL,
  created_at TIMESTAMP DEFAULT now(),
  completed_at TIMESTAMP
);

CREATE TABLE jurors (
  id UUID PRIMARY KEY,
  run_id UUID REFERENCES simulation_runs(id) ON DELETE CASCADE,
  juror_number INT NOT NULL,
  persona_json JSONB NOT NULL
);

CREATE TABLE votes (
  id UUID PRIMARY KEY,
  run_id UUID REFERENCES simulation_runs(id) ON DELETE CASCADE,
  juror_id UUID REFERENCES jurors(id) ON DELETE CASCADE,
  phase TEXT NOT NULL,
  verdict TEXT NOT NULL,
  confidence NUMERIC(4,3) NOT NULL,
  rationale TEXT NOT NULL,
  cited_evidence_codes TEXT[] DEFAULT '{}',
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE deliberation_messages (
  id UUID PRIMARY KEY,
  run_id UUID REFERENCES simulation_runs(id) ON DELETE CASCADE,
  round_no INT NOT NULL,
  turn_no INT NOT NULL,
  juror_id UUID REFERENCES jurors(id) ON DELETE CASCADE,
  message_text TEXT NOT NULL,
  cited_evidence_codes TEXT[] DEFAULT '{}',
  flags_json JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE run_metrics (
  run_id UUID PRIMARY KEY REFERENCES simulation_runs(id) ON DELETE CASCADE,
  initial_split_json JSONB NOT NULL,
  final_split_json JSONB NOT NULL,
  vote_entropy_initial NUMERIC(6,4),
  vote_entropy_final NUMERIC(6,4),
  persuasion_index NUMERIC(6,4),
  citation_coverage NUMERIC(6,4),
  contradiction_rate NUMERIC(6,4),
  dominance_index NUMERIC(6,4),
  generated_at TIMESTAMP DEFAULT now()
);
"""


def upgrade() -> None:
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    op.execute(
        "DROP TABLE IF EXISTS run_metrics, deliberation_messages, votes, jurors, "
        "simulation_runs, evidence_items, cases CASCADE"
    )
