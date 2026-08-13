"""Export a run's votes, transcript, and report as a JSON bundle or CSV."""
import csv
import io

from sqlalchemy.orm import Session

from app import models
from app.services.report import build_report

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _sanitize_csv_cell(value: str) -> str:
    """Neutralize spreadsheet formula injection for values opened in Excel/Sheets."""
    if value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def build_export_bundle(db: Session, run_id) -> dict | None:
    run = db.get(models.SimulationRun, run_id)
    if not run:
        return None

    juror_map = {j.id: j.juror_number for j in run.jurors}

    votes = sorted(
        (
            {
                "juror_number": juror_map.get(v.juror_id),
                "phase": v.phase,
                "verdict": v.verdict,
                "confidence": float(v.confidence),
                "rationale": v.rationale,
                "cited_evidence_codes": v.cited_evidence_codes,
                "what_changed": v.what_changed,
            }
            for v in run.votes
        ),
        key=lambda v: (v["juror_number"], v["phase"]),
    )

    transcript = sorted(
        (
            {
                "round_no": m.round_no,
                "turn_no": m.turn_no,
                "juror_number": juror_map.get(m.juror_id),
                "message": m.message_text,
                "cited_evidence_codes": m.cited_evidence_codes,
                "stance": m.stance,
                "flags": m.flags_json,
            }
            for m in run.messages
        ),
        key=lambda m: (m["round_no"], m["turn_no"]),
    )

    return {
        "run_id": str(run.id),
        "case_id": str(run.case_id),
        "status": run.status,
        "model_name": run.model_name,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "estimated_cost_usd": float(run.estimated_cost_usd) if run.estimated_cost_usd is not None else 0.0,
        "report": build_report(db, run_id),
        "votes": votes,
        "transcript": transcript,
    }


def votes_to_csv(votes: list[dict]) -> str:
    buffer = io.StringIO()
    fieldnames = [
        "juror_number", "phase", "verdict", "confidence",
        "rationale", "cited_evidence_codes", "what_changed",
    ]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for vote in votes:
        writer.writerow({
            "juror_number": vote["juror_number"],
            "phase": _sanitize_csv_cell(vote["phase"]),
            "verdict": _sanitize_csv_cell(vote["verdict"]),
            "confidence": vote["confidence"],
            "rationale": _sanitize_csv_cell(vote["rationale"]),
            "cited_evidence_codes": _sanitize_csv_cell(";".join(vote["cited_evidence_codes"])),
            "what_changed": _sanitize_csv_cell(vote["what_changed"] or ""),
        })
    return buffer.getvalue()
