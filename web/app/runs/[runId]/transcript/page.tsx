import Link from "next/link";
import { notFound } from "next/navigation";
import { getRun, getTranscript, type TranscriptTurn } from "@/lib/api";

function groupByRound(turns: TranscriptTurn[]): Map<number, TranscriptTurn[]> {
  const rounds = new Map<number, TranscriptTurn[]>();
  for (const turn of turns) {
    const existing = rounds.get(turn.round_no) ?? [];
    existing.push(turn);
    rounds.set(turn.round_no, existing);
  }
  return rounds;
}

export default async function TranscriptPage({ params }: { params: { runId: string } }) {
  const [run, transcript] = await Promise.all([getRun(params.runId), getTranscript(params.runId)]);
  if (!run) notFound();

  const rounds = groupByRound(transcript ?? []);

  return (
    <>
      <p>
        <Link href={`/runs/${run.run_id}`}>&larr; Back to run</Link>
      </p>
      <h1>Transcript</h1>
      {rounds.size === 0 ? (
        <p>No deliberation turns recorded yet.</p>
      ) : (
        [...rounds.entries()].map(([roundNo, turns]) => (
          <section key={roundNo}>
            <h2>Round {roundNo}</h2>
            {turns.map((turn) => (
              <div className="turn" key={turn.turn_no}>
                <div className="turn-meta">
                  Turn {turn.turn_no} · Juror #{turn.juror_number ?? "?"}
                </div>
                <p>{turn.message}</p>
                {turn.cited_evidence_codes.length > 0 && (
                  <div className="turn-meta">Cites: {turn.cited_evidence_codes.join(", ")}</div>
                )}
                {Object.entries(turn.flags).some(([, value]) => value === true) && (
                  <div className="flags">
                    Flags:{" "}
                    {Object.entries(turn.flags)
                      .filter(([, value]) => value === true)
                      .map(([key]) => key)
                      .join(", ")}
                  </div>
                )}
              </div>
            ))}
          </section>
        ))
      )}
    </>
  );
}
