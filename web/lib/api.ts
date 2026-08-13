const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type RunListItem = {
  run_id: string;
  case_id: string;
  case_title: string | null;
  status: string;
  model_name: string;
  created_at: string;
  completed_at: string | null;
};

export type RunDetail = {
  run_id: string;
  status: string;
  model_name: string;
  created_at: string;
  completed_at: string | null;
};

export type TranscriptTurn = {
  round_no: number;
  turn_no: number;
  juror_number: number | null;
  message: string;
  cited_evidence_codes: string[];
  flags: Record<string, unknown>;
};

export type VerdictSplit = {
  guilty: number;
  not_guilty: number;
  undecided: number;
};

export type VoteShift = {
  juror_number: number;
  from: string;
  to: string;
  confidence_from: number;
  confidence_to: number;
  changed: boolean;
};

export type RunReport = {
  run_id: string;
  status: string;
  initial_split: VerdictSplit;
  final_split: VerdictSplit;
  vote_shifts: VoteShift[];
  warnings: string[];
  metrics: Record<string, number>;
};

async function fetchJson<T>(path: string): Promise<T | null> {
  const res = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Request to ${path} failed with status ${res.status}`);
  return res.json() as Promise<T>;
}

export function listRuns(): Promise<RunListItem[] | null> {
  return fetchJson<RunListItem[]>("/runs");
}

export function getRun(runId: string): Promise<RunDetail | null> {
  return fetchJson<RunDetail>(`/runs/${runId}`);
}

export function getTranscript(runId: string): Promise<TranscriptTurn[] | null> {
  return fetchJson<TranscriptTurn[]>(`/runs/${runId}/transcript`);
}

export function getReport(runId: string): Promise<RunReport | null> {
  return fetchJson<RunReport>(`/runs/${runId}/report`);
}

export type ChargeElement = { id: string; description: string };

export type ChargeElements = {
  jurisdiction: string;
  charge: string;
  statute_reference: string | null;
  standard_of_proof: string;
  elements: ChargeElement[];
};

export type EvidenceItemInput = {
  code: string;
  kind: string;
  content: string;
};

export type CasePacketInput = {
  title: string;
  jurisdiction?: string | null;
  charge?: string | null;
  standard_of_proof: string;
  facts: string[];
  jury_instructions: string;
  evidence_items: EvidenceItemInput[];
};

export type CaseOut = { id: string; title: string };

export type RunCreateInput = {
  case_id: string;
  model_name: string;
  max_rounds: number;
  juror_count: number;
  seed: number;
};

export type RunCreateResult = { run_id: string; status: string };

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET ${path} failed with status ${res.status}`);
  return res.json() as Promise<T>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`POST ${path} failed with status ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const listJurisdictions = () => getJson<string[]>("/legal/jurisdictions");
export const listCharges = (jurisdiction: string) => getJson<string[]>(`/legal/${jurisdiction}/charges`);
export const getChargeElements = (jurisdiction: string, slug: string) =>
  getJson<ChargeElements>(`/legal/${jurisdiction}/charges/${slug}`);
export const listDefenses = (jurisdiction: string) => getJson<string[]>(`/legal/${jurisdiction}/defenses`);

export const createCase = (payload: CasePacketInput) => postJson<CaseOut>("/cases", payload);
export const createRun = (payload: RunCreateInput) => postJson<RunCreateResult>("/runs", payload);

