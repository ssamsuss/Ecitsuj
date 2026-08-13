from fastapi import APIRouter, HTTPException

from app.services import legal

router = APIRouter(prefix="/legal", tags=["legal"])


@router.get("/jurisdictions")
def get_jurisdictions():
    return legal.list_jurisdictions()


@router.get("/{jurisdiction}/charges")
def list_charges(jurisdiction: str):
    return legal.list_charges(jurisdiction)


@router.get("/{jurisdiction}/charges/{charge_slug}")
def get_charge_elements(jurisdiction: str, charge_slug: str):
    try:
        return legal.load_charge_elements(jurisdiction, charge_slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="charge not found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{jurisdiction}/jury-instructions")
def list_jury_instructions(jurisdiction: str):
    return legal.list_jury_instructions(jurisdiction)


@router.get("/{jurisdiction}/jury-instructions/{instruction_slug}")
def get_jury_instruction(jurisdiction: str, instruction_slug: str):
    try:
        doc = legal.load_jury_instruction(jurisdiction, instruction_slug)
        return {"metadata": doc.metadata, "body": doc.body}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="jury instruction not found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{jurisdiction}/standards")
def list_standards(jurisdiction: str):
    return legal.list_legal_standards(jurisdiction)


@router.get("/{jurisdiction}/standards/{standard_slug}")
def get_standard(jurisdiction: str, standard_slug: str):
    try:
        doc = legal.load_legal_standard(jurisdiction, standard_slug)
        return {"metadata": doc.metadata, "body": doc.body}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="legal standard not found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/{jurisdiction}/defenses")
def get_defenses(jurisdiction: str):
    return legal.list_defenses(jurisdiction)
