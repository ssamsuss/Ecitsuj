"use client";

import { useState } from "react";
import type { RunReport, TranscriptTurn } from "@/lib/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const PRIMARY_METRICS = ["citation_coverage", "contradiction_rate", "dominance_index"] as const;

type Tab = "votes" | "shifts" | "transcript" | "metrics" | "export";

function groupByRound(turns: TranscriptTurn[]): Map<number, TranscriptTurn[]> {
  const rounds = new Map<number, TranscriptTurn[]>();
  for (const turn of turns) {
    const existing = rounds.get(turn.round_no) ?? [];
    existing.push(turn);
    rounds.set(turn.round_no, existing);
  }
  return rounds;
}

export default function ResultsPanel({
  runId,
  report,
  transcript,
}: {
  runId: string;
  report: RunReport;
  transcript: TranscriptTurn[];
}) {
  const [tab, setTab] = useState<Tab>("votes");
  const rounds = groupByRound(transcript);
  const secondaryMetrics = Object.entries(report.metrics).filter(
    ([label]) => !(PRIMARY_METRICS as readonly string[]).includes(label)
  );

  return (
    <section>
      <div className="tab-bar">
        {(
          [
            ["votes", "Vote Summary"],
            ["shifts", "Juror Shifts"],
            ["transcript", "Transcript"],
            ["metrics", "Metrics"],
            ["export", "Export"],
          ] as [Tab, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            className={`tab-button ${tab === key ? "tab-button-active" : ""}`}
            onClick={() => setTab(key)}
            type="button"
          >
            {label}
          </button>
        ))}
      </div>

      {report.warnings.length > 0 && (
        <div className="flags">
          <strong>Warnings:</strong>
          <ul>
            {report.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      {tab === "votes" && (
        <table>
          <thead>
            <tr>
              <th></th>
              <th>Guilty</th>
              <th>Not guilty</th>
              <th>Undecided</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Initial</td>
              <td>{report.initial_split.guilty}</td>
              <td>{report.initial_split.not_guilty}</td>
              <td>{report.initial_split.undecided}</td>
            </tr>
            <tr>
              <td>Final</td>
              <td>{report.final_split.guilty}</td>
              <td>{report.final_split.not_guilty}</td>
              <td>{report.final_split.undecided}</td>
            </tr>
          </tbody>
        </table>
      )}

      {tab === "shifts" && (
        <table>
          <thead>
            <tr>
              <th>Juror</th>
              <th>From</th>
              <th>To</th>
              <th>Confidence (initial → final)</th>
              <th>Changed</th>
            </tr>
          </thead>
          <tbody>
            {report.vote_shifts.map((shift) => (
              <tr key={shift.juror_number}>
                <td>#{shift.juror_number}</td>
                <td>{shift.from}</td>
                <td>{shift.to}</td>
                <td>
                  {shift.confidence_from.toFixed(2)} → {shift.confidence_to.toFixed(2)}
                </td>
                <td>{shift.changed ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {tab === "transcript" &&
        (rounds.size === 0 ? (
          <p>No deliberation turns recorded.</p>
        ) : (
          [...rounds.entries()].map(([roundNo, turns]) => (
            <div key={roundNo}>
              <h3>Round {roundNo}</h3>
              {turns.map((turn) => (
                <div className="turn" key={turn.turn_no}>
                  <div className="turn-meta">
                    Turn {turn.turn_no} · Juror #{turn.juror_number ?? "?"}
                  </div>
                  <p>{turn.message}</p>
                  {turn.cited_evidence_codes.length > 0 && (
                    <div className="turn-meta">Cites: {turn.cited_evidence_codes.join(", ")}</div>
                  )}
                </div>
              ))}
            </div>
          ))
        ))}

      {tab === "metrics" && (
        <>
          <div className="metrics-grid">
            {PRIMARY_METRICS.map((label) => (
              <div className="metric" key={label}>
                <div className="metric-label">{label}</div>
                <div className="metric-value">{(report.metrics[label] ?? 0).toFixed(3)}</div>
              </div>
            ))}
          </div>
          <div className="metrics-grid">
            {secondaryMetrics.map(([label, value]) => (
              <div className="metric" key={label}>
                <div className="metric-label">{label}</div>
                <div className="metric-value">{value.toFixed(3)}</div>
              </div>
            ))}
          </div>
        </>
      )}

      {tab === "export" && (
        <p>
          <a href={`${API_BASE_URL}/runs/${runId}/export?format=json`}>Download JSON</a>
          {" · "}
          <a href={`${API_BASE_URL}/runs/${runId}/export?format=csv`}>Download CSV (votes)</a>
        </p>
      )}
    </section>
  );
}
