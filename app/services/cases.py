"""Case ingestion: persist case packets and build a tagged evidence index."""
import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app import models, schemas

_KIND_TAGS: dict[str, tuple[str, ...]] = {
    "witness": ("testimonial",),
    "forensic": ("scientific", "physical"),
    "exhibit": ("documentary",),
}

_KEYWORD_TAGS: dict[str, str] = {
    "fingerprint": "forensic:fingerprint",
    "dna": "forensic:dna",
    "cctv": "video",
    "video": "video",
    "audio": "audio",
    "recording": "audio",
    "confession": "confession",
    "alibi": "alibi",
    "eyewitness": "eyewitness",
    "text message": "digital:messages",
    "email": "digital:email",
    "phone": "digital:phone-records",
}


def tag_evidence_item(kind: str, content: str) -> list[str]:
    """Derive index tags for an evidence item from its kind and content."""
    tags = set(_KIND_TAGS.get(kind.lower(), ()))
    lowered = content.lower()
    for keyword, tag in _KEYWORD_TAGS.items():
        if re.search(re.escape(keyword), lowered):
            tags.add(tag)
    return sorted(tags)


@dataclass(frozen=True)
class EvidenceIndexEntry:
    code: str
    kind: str
    content: str
    tags: list[str] = field(default_factory=list)


def build_evidence_index(case: models.Case) -> dict[str, EvidenceIndexEntry]:
    """Build a code-keyed evidence index with each item's stored tags."""
    return {
        item.evidence_code: EvidenceIndexEntry(
            code=item.evidence_code,
            kind=item.kind,
            content=item.content,
            tags=sorted((item.metadata_json or {}).get("tags", [])),
        )
        for item in case.evidence_items
    }


def ingest_case_packet(db: Session, payload: schemas.CasePacketIn) -> models.Case:
    """Persist a validated case packet and tag its evidence items for indexing."""
    case = models.Case(
        title=payload.title,
        jurisdiction=payload.jurisdiction,
        charge=payload.charge,
        standard_of_proof=payload.standard_of_proof,
        facts_json={"facts": payload.facts},
        instructions_text=payload.jury_instructions,
    )
    db.add(case)
    db.flush()

    for item in payload.evidence_items:
        metadata = {**item.metadata, "tags": tag_evidence_item(item.kind, item.content)}
        db.add(models.EvidenceItem(
            case_id=case.id,
            evidence_code=item.code,
            kind=item.kind,
            content=item.content,
            metadata_json=metadata,
        ))

    db.commit()
    db.refresh(case)
    return case
