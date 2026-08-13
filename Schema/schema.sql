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
  evidence_code TEXT NOT NULL, -- E1, E2...
  kind TEXT NOT NULL,          -- witness, forensic, exhibit
  content TEXT NOT NULL,
  metadata_json JSONB DEFAULT '{}'::jsonb,
  CONSTRAINT uq_evidence_items_case_code UNIQUE (case_id, evidence_code)
);

CREATE TABLE simulation_runs (
  id UUID PRIMARY KEY,
  case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
  model_name TEXT NOT NULL,
  temperature NUMERIC(3,2) DEFAULT 0.4,
  status TEXT NOT NULL, -- queued|running|done|failed
  config_json JSONB NOT NULL, -- rounds, juror count, etc.
  created_at TIMESTAMP DEFAULT now(),
  completed_at TIMESTAMP,
  estimated_cost_usd NUMERIC(10,4) -- rough character-based cost estimate
);

CREATE TABLE jurors (
  id UUID PRIMARY KEY,
  run_id UUID REFERENCES simulation_runs(id) ON DELETE CASCADE,
  juror_number INT NOT NULL, -- 1..12
  persona_json JSONB NOT NULL
);

CREATE TABLE votes (
  id UUID PRIMARY KEY,
  run_id UUID REFERENCES simulation_runs(id) ON DELETE CASCADE,
  juror_id UUID REFERENCES jurors(id) ON DELETE CASCADE,
  phase TEXT NOT NULL, -- initial|final
  verdict TEXT NOT NULL, -- guilty|not_guilty|undecided
  confidence NUMERIC(4,3) NOT NULL, -- 0..1
  rationale TEXT NOT NULL,
  cited_evidence_codes TEXT[] DEFAULT '{}',
  what_changed TEXT, -- final-phase only: what changed since the initial vote
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
  stance TEXT, -- support|challenge|clarify
  flags_json JSONB DEFAULT '{}'::jsonb -- new_fact_flag, contradiction_flag
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
  dominance_index NUMERIC(6,4), -- concentration of speaking time
  generated_at TIMESTAMP DEFAULT now()
);