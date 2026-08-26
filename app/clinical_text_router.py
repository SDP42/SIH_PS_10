"""
Human clinical-text -> terminology candidate API — mounted under
/api/v1/clinical-text. First use of the /api/v1 prefix in this codebase,
deliberately: API versioning is independent of terminology-release
versioning (2025-01, 2026-01) — see the platform strategy doc, §20.

Every response here is built to never look like a diagnosis. See
app/clinical_nlp.py's SAFETY_NOTE before changing either file.
"""
from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app import clinical_nlp

router = APIRouter(prefix="/api/v1/clinical-text", tags=["Clinical Text Assistant"])


class ClinicalTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Free-text clinical note or patient-reported complaint")


@router.post("/extract")
def extract_symptoms(body: ClinicalTextRequest) -> Dict[str, Any]:
    """
    Extraction only — symptoms, negation, duration, body site, laterality.
    No terminology search yet. Useful for showing a clinician what the
    system understood before it goes looking for codes.
    """
    extracted = clinical_nlp.extract(body.text)
    return {
        "input_text": body.text,
        "extracted": extracted,
        "diagnosis_inferred": False,
        "safety_note": clinical_nlp.SAFETY_NOTE,
    }


@router.post("/candidates")
def get_candidates(body: ClinicalTextRequest) -> Dict[str, Any]:
    """
    Full Phase 1 pipeline: extraction + real terminology search across
    NAMASTE (all three living traditions) and ICD-11. Negated symptoms are
    shown but never searched. Never returns a diagnosis — every result is
    presented as a candidate requiring explicit clinician confirmation.
    """
    return clinical_nlp.build_candidates(body.text)
