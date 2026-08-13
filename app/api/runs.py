from uuid import UUID
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.db import get_db
from app import schemas
from app.services.simulation import run_simulation
from app.services.report import build_report
from app.services.export import build_export_bundle, votes_to_csv
from app import models

router = APIRouter(prefix="/runs", tags=["runs"])

@router.get("")
def list_runs(db: Session = Depends(get_db)):
    runs = db.query(models.SimulationRun).order_by(models.SimulationRun.created_at.desc()).all()
    return [
        {
            "run_id": str(r.id),
            "case_id": str(r.case_id),
            "case_title": r.case.title if r.case else None,
            "status": r.status,
            "model_name": r.model_name,
            "created_at": r.created_at,
            "completed_at": r.completed_at,
        }
        for r in runs
    ]

@router.post("")
def create_run(payload: schemas.RunCreateIn, db: Session = Depends(get_db)):
    try:
        run = run_simulation(db, payload)
        return {"run_id": str(run.id), "status": run.status}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{run_id}")
def get_run(run_id: UUID, db: Session = Depends(get_db)):
    run = db.get(models.SimulationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return {
        "run_id": str(run.id),
        "status": run.status,
        "model_name": run.model_name,
        "created_at": run.created_at,
        "completed_at": run.completed_at,
        "estimated_cost_usd": float(run.estimated_cost_usd) if run.estimated_cost_usd is not None else 0.0,
    }

@router.get("/{run_id}/transcript")
def get_transcript(run_id: UUID, db: Session = Depends(get_db)):
    run = db.get(models.SimulationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    juror_map = {j.id: j.juror_number for j in run.jurors}
    rows = sorted(run.messages, key=lambda x: (x.round_no, x.turn_no))
    return [
        {
            "round_no": m.round_no,
            "turn_no": m.turn_no,
            "juror_number": juror_map.get(m.juror_id),
            "message": m.message_text,
            "cited_evidence_codes": m.cited_evidence_codes,
            "stance": m.stance,
            "flags": m.flags_json
        }
        for m in rows
    ]

@router.get("/{run_id}/report", response_model=schemas.RunReportOut)
def get_report(run_id: UUID, db: Session = Depends(get_db)):
    report = build_report(db, run_id)
    if not report:
        raise HTTPException(status_code=404, detail="run not found")
    return report

@router.get("/{run_id}/export")
def export_run(
    run_id: UUID,
    export_format: str = Query("json", alias="format", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
):
    bundle = build_export_bundle(db, run_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="run not found")

    if export_format == "csv":
        return Response(
            content=votes_to_csv(bundle["votes"]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="run-{run_id}-votes.csv"'},
        )

    return Response(
        content=json.dumps(bundle, default=str, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="run-{run_id}.json"'},
    )