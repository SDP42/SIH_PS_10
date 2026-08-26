"""
FHIR ProblemList entry builder — the concrete deliverable named in the spec's
demonstration item (c): "construct a FHIR ProblemList entry" from a searched
NAMASTE term. Reuses the same dual-coding logic as $translate/Bundle.
"""
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import fhir_extra

router = APIRouter(prefix="/api/problem-list", tags=["ProblemList"])


class BuildProblemListRequest(BaseModel):
    namaste_code: str
    source_system: Optional[str] = "NAMASTE"
    patient_reference: str = "Patient/demo-patient"


@router.post("/build")
def build_problem_list_entry(body: BuildProblemListRequest) -> Dict[str, Any]:
    """
    Builds a FHIR Condition resource (a "Problem List" entry per US Core /
    IPS convention: Condition.category = problem-list-item) carrying the
    original NAMASTE coding plus real double-coded TM2 + Biomedicine codes.
    """
    normalized_code = re.sub(r"\s+", " ", body.namaste_code).strip()
    match_parts, unknown_message = fhir_extra.dual_translate_match_parts(
        normalized_code, ["ICD-11 TM2", "ICD-11 Biomedicine"], body.source_system or ""
    )

    if unknown_message and not match_parts:
        raise HTTPException(status_code=404, detail={"error": "SOURCE_NOT_FOUND", "message": unknown_message})

    codings = [{
        "system": fhir_extra.SYSTEM_URIS.get((body.source_system or "NAMASTE").upper(), fhir_extra.SYSTEM_URIS["NAMASTE"]),
        "code": normalized_code,
    }]
    contained_provenance = []

    for part in match_parts:
        fields = {p["name"]: p for p in part["part"]}
        if fields["equivalence"]["valueCode"] == "unmatched":
            continue
        concept = dict(fields["concept"]["valueCoding"])
        concept["extension"] = [{
            "url": fhir_extra.MAPPING_EQUIVALENCE_EXT_URL,
            "valueCode": fields["equivalence"]["valueCode"],
        }]
        codings.append(concept)
        if "provenance" in fields:
            contained_provenance.append(fields["provenance"]["resource"])

    condition = {
        "resourceType": "Condition",
        "id": f"problem-{normalized_code.replace(' ', '-').replace('(', '').replace(')', '')}",
        "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
        "category": [{"coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/condition-category",
            "code": "problem-list-item",
            "display": "Problem List Item",
        }]}],
        "code": {"coding": codings},
        "subject": {"reference": body.patient_reference},
        "recordedDate": datetime.now(timezone.utc).isoformat(),
        "contained": contained_provenance,
    }
    return condition
