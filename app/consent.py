"""
Minimal FHIR Consent stub.

NOT a real consent-management system — no consent is ever actually
collected or verified. This exists only so a Bundle-upload response has
something correctly-shaped to reference when the spec asks for "consent
metadata." Real consent capture/verification (patient-facing UI, revocation,
ABDM Consent Manager integration) is out of scope for this pass.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/Consent", tags=["Consent (stub)"])

_STUB_CONSENT_ID = "demo-consent-001"


@router.get("/{consent_id}")
def get_consent(consent_id: str):
    if consent_id != _STUB_CONSENT_ID:
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": f"Only the stub consent '{_STUB_CONSENT_ID}' exists in this demo."},
        )
    return {
        "resourceType": "Consent",
        "id": _STUB_CONSENT_ID,
        "status": "active",
        "scope": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/consentscope", "code": "patient-privacy"}]},
        "category": [{"coding": [{"system": "http://loinc.org", "code": "59284-0", "display": "Patient Consent"}]}],
        "patient": {"reference": "Patient/demo-patient"},
        "dateTime": datetime.now(timezone.utc).isoformat(),
        "policyRule": {"text": "Demo-mode stub — no real consent was collected or verified."},
    }
