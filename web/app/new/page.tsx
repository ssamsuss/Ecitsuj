"use client";

import { useEffect, useMemo, useState } from "react";
import {
  createCase,
  createRun,
  getReport,
  getTranscript,
  listCharges,
  listDefenses,
  listJurisdictions,
  getChargeElements,
  type ChargeElements,
  type RunReport,
  type TranscriptTurn,
} from "@/lib/api";
import { validateCaseSetup, isValid, type EvidenceItemDraft } from "@/lib/validation";
import ResultsPanel from "./ResultsPanel";

const MODEL_OPTIONS = ["gpt-4.1", "gpt-4o", "gpt-4o-mini"];

type RunState = "idle" | "submitting" | "done" | "error";

export default function NewSimulationPage() {
  // Case Setup
  const [jurisdictions, setJurisdictions] = useState<string[]>([]);
  const [jurisdiction, setJurisdiction] = useState("");
  const [charges, setCharges] = useState<string[]>([]);
  const [chargeSlug, setChargeSlug] = useState("");
  const [chargeElements, setChargeElements] = useState<ChargeElements | null>(null);
  const [defenseOptions, setDefenseOptions] = useState<string[]>([]);
  const [selectedDefenses, setSelectedDefenses] = useState<string[]>([]);
  const [standardOfProof, setStandardOfProof] = useState("beyond a reasonable doubt");
  const [factsText, setFactsText] = useState("");
  const [evidenceItems, setEvidenceItems] = useState<EvidenceItemDraft[]>([
    { code: "E1", kind: "witness", content: "" },
  ]);

  // Simulation Controls
  const [jurorCount, setJurorCount] = useState(12);
  const [maxRounds, setMaxRounds] = useState(4);
  const [model, setModel] = useState(MODEL_OPTIONS[0]);
  const [seed, setSeed] = useState(42);

  // Live Run Status / Results
  const [runState, setRunState] = useState<RunState>("idle");
  const [runId, setRunId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [report, setReport] = useState<RunReport | null>(null);
  const [transcript, setTranscript] = useState<TranscriptTurn[]>([]);

  useEffect(() => {
    listJurisdictions().then(setJurisdictions).catch(() => setJurisdictions([]));
  }, []);

  useEffect(() => {
    if (!jurisdiction) return;
    setChargeSlug("");
    setChargeElements(null);
    listCharges(jurisdiction).then(setCharges).catch(() => setCharges([]));
    listDefenses(jurisdiction).then(setDefenseOptions).catch(() => setDefenseOptions([]));
  }, [jurisdiction]);

  useEffect(() => {
    if (!jurisdiction || !chargeSlug) return;
    getChargeElements(jurisdiction, chargeSlug)
      .then((data) => {
        setChargeElements(data);
        setStandardOfProof(data.standard_of_proof);
      })
      .catch(() => setChargeElements(null));
  }, [jurisdiction, chargeSlug]);

  const facts = useMemo(
    () => factsText.split("\n").map((f) => f.trim()).filter(Boolean),
    [factsText]
  );

  const validationErrors = useMemo(
    () => validateCaseSetup(chargeElements?.charge ?? chargeSlug, facts, evidenceItems),
    [chargeElements, chargeSlug, facts, evidenceItems]
  );
  const canDeliberate = isValid(validationErrors) && runState !== "submitting";

  function updateEvidenceRow(index: number, patch: Partial<EvidenceItemDraft>) {
    setEvidenceItems((rows) => rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  }

  function addEvidenceRow() {
    const nextNumber = evidenceItems.length + 1;
    setEvidenceItems((rows) => [...rows, { code: `E${nextNumber}`, kind: "witness", content: "" }]);
  }

  function removeEvidenceRow(index: number) {
    setEvidenceItems((rows) => rows.filter((_, i) => i !== index));
  }

  async function handleDeliberate() {
    if (!canDeliberate) return;
    setRunState("submitting");
    setErrorMessage(null);
    setReport(null);
    setTranscript([]);

    try {
      const chargeTitle = chargeElements?.charge ?? chargeSlug;
      const title = jurisdiction ? `${chargeTitle} (${jurisdiction})` : chargeTitle;
      const elementLines = (chargeElements?.elements ?? []).map((el) => `- ${el.description}`).join("\n");
      const juryInstructions = [
        `Standard of proof: ${standardOfProof}.`,
        elementLines ? `Elements the jury must find:\n${elementLines}` : null,
        selectedDefenses.length > 0 ? `Defenses raised: ${selectedDefenses.join(", ")}.` : null,
      ]
        .filter(Boolean)
        .join("\n\n");

      const caseOut = await createCase({
        title,
        jurisdiction: jurisdiction || null,
        charge: chargeTitle || null,
        standard_of_proof: standardOfProof,
        facts,
        jury_instructions: juryInstructions,
        evidence_items: evidenceItems.map((item) => ({
          code: item.code.trim(),
          kind: item.kind.trim(),
          content: item.content.trim(),
        })),
      });

      const run = await createRun({
        case_id: caseOut.id,
        model_name: model,
        juror_count: jurorCount,
        max_rounds: maxRounds,
        seed,
      });

      setRunId(run.run_id);

      if (run.status !== "done") {
        setRunState("error");
        setErrorMessage(`Run finished with status: ${run.status}`);
        return;
      }

      const [reportResult, transcriptResult] = await Promise.all([
        getReport(run.run_id),
        getTranscript(run.run_id),
      ]);
      setReport(reportResult);
      setTranscript(transcriptResult ?? []);
      setRunState("done");
    } catch (err) {
      setRunState("error");
      setErrorMessage(err instanceof Error ? err.message : String(err));
    }
  }

  const lastTurn = transcript.length > 0 ? transcript[transcript.length - 1] : null;

  return (
    <div className="new-sim-layout">
      <section className="panel">
        <h2>Case Setup</h2>

        <label>
          Jurisdiction
          <select value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)}>
            <option value="">Select jurisdiction…</option>
            {jurisdictions.map((j) => (
              <option key={j} value={j}>
                {j}
              </option>
            ))}
          </select>
        </label>

        <label>
          Charge / Article
          <select
            value={chargeSlug}
            onChange={(e) => setChargeSlug(e.target.value)}
            disabled={!jurisdiction}
          >
            <option value="">Select charge…</option>
            {charges.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>

        <label>
          Defenses
          <select
            multiple
            value={selectedDefenses}
            onChange={(e) =>
              setSelectedDefenses(Array.from(e.target.selectedOptions, (o) => o.value))
            }
            size={Math.min(6, Math.max(3, defenseOptions.length))}
          >
            {defenseOptions.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>

        <label>
          Standard of proof
          <input
            type="text"
            value={standardOfProof}
            onChange={(e) => setStandardOfProof(e.target.value)}
          />
        </label>

        <label>
          Case facts (one per line)
          <textarea
            rows={5}
            value={factsText}
            onChange={(e) => setFactsText(e.target.value)}
            placeholder="Defendant seen near store at 10:03 PM"
          />
        </label>
        {validationErrors.facts && <p className="field-error">{validationErrors.facts}</p>}

        <h3>Evidence items</h3>
        {evidenceItems.map((item, index) => (
          <div className="evidence-row" key={index}>
            <input
              type="text"
              placeholder="Code (E1)"
              value={item.code}
              onChange={(e) => updateEvidenceRow(index, { code: e.target.value })}
            />
            <input
              type="text"
              placeholder="Type (witness, forensic, exhibit...)"
              value={item.kind}
              onChange={(e) => updateEvidenceRow(index, { kind: e.target.value })}
            />
            <input
              type="text"
              placeholder="Evidence text"
              value={item.content}
              onChange={(e) => updateEvidenceRow(index, { content: e.target.value })}
            />
            <button type="button" onClick={() => removeEvidenceRow(index)} aria-label="Remove row">
              &times;
            </button>
            {validationErrors.evidenceRowErrors[index] && (
              <p className="field-error">{validationErrors.evidenceRowErrors[index]}</p>
            )}
          </div>
        ))}
        <button type="button" onClick={addEvidenceRow}>
          + Add evidence item
        </button>
        {validationErrors.evidenceItems && <p className="field-error">{validationErrors.evidenceItems}</p>}
      </section>

      <section className="panel">
        <h2>Simulation Controls</h2>

        <label>
          Juror count
          <input
            type="number"
            min={1}
            max={12}
            value={jurorCount}
            onChange={(e) => setJurorCount(Number(e.target.value))}
          />
        </label>

        <label>
          Max rounds
          <input
            type="number"
            min={1}
            value={maxRounds}
            onChange={(e) => setMaxRounds(Number(e.target.value))}
          />
        </label>

        <label>
          Model
          <select value={model} onChange={(e) => setModel(e.target.value)}>
            {MODEL_OPTIONS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>

        <label>
          Seed
          <input type="number" value={seed} onChange={(e) => setSeed(Number(e.target.value))} />
        </label>

        <button
          type="button"
          className="deliberate-button"
          disabled={!canDeliberate}
          onClick={handleDeliberate}
        >
          {runState === "submitting" ? "Deliberating…" : "Deliberate"}
        </button>

        <section className="live-status">
          <h3>Live Run Status</h3>
          <p>
            Status:{" "}
            <span className={`badge badge-${runState === "submitting" ? "running" : runState === "done" ? "done" : runState === "error" ? "failed" : ""}`}>
              {runState === "idle" && "queued"}
              {runState === "submitting" && "running"}
              {runState === "done" && "done"}
              {runState === "error" && "failed"}
            </span>
          </p>
          <p>
            Round: {runState === "done" ? `${maxRounds}/${maxRounds}` : "—"} · Current speaker:{" "}
            {lastTurn ? `Juror #${lastTurn.juror_number}` : "—"}
          </p>
          <p>Estimated cost: {report ? `$${(report.metrics.estimated_cost_usd ?? 0).toFixed(4)}` : "—"}</p>
          <p className="turn-meta">
            Status updates once the deliberation completes (the current engine runs synchronously).
          </p>
          {errorMessage && <p className="field-error">{errorMessage}</p>}
        </section>
      </section>

      {report && runId && (
        <div className="results-panel">
          <h2>Results</h2>
          <ResultsPanel runId={runId} report={report} transcript={transcript} />
        </div>
      )}
    </div>
  );
}
