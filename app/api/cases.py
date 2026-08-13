from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.db import get_db
from app.services.cases import build_evidence_index, ingest_case_packet

router = APIRouter(prefix="/cases", tags=["cases"])

@router.post("", response_model=schemas.CaseOut, status_code=201)
def create_case(payload: schemas.CasePacketIn, db: Session = Depends(get_db)):
    return ingest_case_packet(db, payload)

@router.get("/{case_id}/evidence", response_model=list[schemas.EvidenceIndexEntryOut])
def get_evidence_index(case_id: UUID, db: Session = Depends(get_db)):
    case = db.get(models.Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="case not found")
    return list(build_evidence_index(case).values())