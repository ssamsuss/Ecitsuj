import Link from "next/link";
import { notFound } from "next/navigation";
import { getRun, getReport } from "@/lib/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default async function RunDetailPage({ params }: { params: { runId: string } }) {
  const [run, report] = await Promise.all([getRun(params.runId), getReport(params.runId)]);
  if (!run) notFound();

  return (
    <>
      <h1>Run {run.run_id}</h1>
      <p>
        Status: <span className={`badge badge-${run.status}`}>{run.status}</span>
      </p>
      <p>Model: {run.model_name}</p>
      <p>Created: {new Date(run.created_at).toLocaleString()}</p>
      {run.completed_at && <p>Completed: {new Date(run.completed_at).toLocaleString()}</p>}
      <p>
        <Link href={`/runs/${run.run_id}/transcript`}>View transcript</Link>
      </p>
      <p>
        Export: <a href={`${API_BASE_URL}/runs/${run.run_id}/export?format=json`}>JSON</a>{" "}
        · <a href={`${API_BASE_URL}/runs/${run.run_id}/export?format=csv`}>CSV (votes)</a>
      </p>

      {report && (
        <>
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

          <h2>Verdict splits</h2>
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

          <h2>Metrics</h2>
          <div className="metrics-grid">
            {Object.entries(report.metrics).map(([label, value]) => (
              <div className="metric" key={label}>
                <div className="metric-label">{label}</div>
                <div className="metric-value">{value.toFixed(3)}</div>
              </div>
            ))}
          </div>

          <h2>Vote shifts</h2>
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
        </>
      )}
    </>
  );
}
