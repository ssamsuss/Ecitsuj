import Link from "next/link";
import { listRuns } from "@/lib/api";

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

export default async function RunListPage() {
  const runs = await listRuns();

  return (
    <>
      <h1>Runs</h1>
      {!runs || runs.length === 0 ? (
        <p>No runs yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Case</th>
              <th>Status</th>
              <th>Model</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.run_id}>
                <td>
                  <Link href={`/runs/${run.run_id}`}>{run.case_title ?? run.case_id}</Link>
                </td>
                <td>
                  <StatusBadge status={run.status} />
                </td>
                <td>{run.model_name}</td>
                <td>{new Date(run.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
