"""
Shared FHIR conformance helpers: structured OperationOutcome for errors, and
the CapabilityStatement describing what this server actually supports.

Scope note: this is applied to the new /api/v1/* surface (Phase 2 of the
platform strategy roadmap), not retrofitted across every pre-existing
endpoint — the older routes' custom `{error, message}` error shape stays as
it is for backward compatibility with the existing frontend, which already
parses that shape. New v1 endpoints use OperationOutcome from the start.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fhir.resources.operationoutcome import OperationOutcome, OperationOutcomeIssue


def operation_outcome(severity: str, code: str, diagnostics: str) -> Dict[str, Any]:
    """
    Build a real FHIR R4 OperationOutcome. `severity` is one of fatal|error|
    warning|information; `code` is a FHIR IssueType (e.g. 'login', 'forbidden',
    'throttled', 'not-found', 'invalid', 'processing').
    """
    outcome = OperationOutcome(
        issue=[OperationOutcomeIssue(severity=severity, code=code, diagnostics=diagnostics)]
    )
    return outcome.dict()


def build_capability_statement(base_url: str = "") -> Dict[str, Any]:
    """
    Hand-assembled FHIR R4 CapabilityStatement JSON reflecting only resources
    and operations this service genuinely implements today. Never claims an
    operation ($validate-code, $expand, $translate) that doesn't have a real
    handler behind it — see the platform strategy doc §15 for exactly what
    is implemented vs. proposed at the time this was written.
    """
    now = datetime.now(timezone.utc).isoformat()
    return {
        "resourceType": "CapabilityStatement",
        "status": "active",
        "date": now,
        "publisher": "NAMASTE-ICD11 Integration Service",
        "kind": "instance",
        "software": {
            "name": "NAMASTE x ICD-11 Terminology Microservice",
            "version": "0.1.0",
        },
        "implementation": {
            "description": "AYUSH NAMASTE <-> ICD-11 (TM2 + Biomedicine) FHIR R4 terminology bridge",
            "url": base_url or "http://localhost:8000",
        },
        "fhirVersion": "4.0.1",
        "format": ["json"],
        "rest": [
            {
                "mode": "server",
                "resource": [
                    {
                        "type": "ConceptMap",
                        "interaction": [{"code": "read"}, {"code": "search-type"}],
                        "operation": [{"name": "translate", "definition": "http://hl7.org/fhir/OperationDefinition/ConceptMap-translate"}],
                    },
                    {
                        "type": "CodeSystem",
                        "interaction": [{"code": "read"}],
                    },
                    {
                        "type": "ValueSet",
                        "operation": [{"name": "expand", "definition": "http://hl7.org/fhir/OperationDefinition/ValueSet-expand"}],
                    },
                    {
                        "type": "Bundle",
                        "interaction": [{"code": "create"}],
                    },
                    {
                        "type": "Condition",
                        "interaction": [{"code": "create"}],
                    },
                    {
                        "type": "Consent",
                        "interaction": [{"code": "read"}],
                        "documentation": "Static stub resource only — no consent is actually collected or verified. See README.",
                    },
                ],
                "operation": [
                    {"name": "validate-code", "definition": "http://hl7.org/fhir/OperationDefinition/CodeSystem-validate-code"},
                ],
            }
        ],
        "extension": [
            {
                "url": "http://namaste.terminology/fhir/StructureDefinition/conformance-honesty-note",
                "valueString": (
                    "This CapabilityStatement lists only operations with a real handler behind them. "
                    "Consent is a labeled stub. Real ABHA OAuth2 is not implemented — see README 'What's "
                    "real vs. demo-mode'."
                ),
            }
        ],
    }
