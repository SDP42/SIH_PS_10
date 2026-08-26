"""
FastAPI dependency that gates the /api/v1/* public surface on an API key —
separate from app/auth.py's clinician-facing demo bearer token.

Usage: `Depends(require_api_key("search:read"))` in a route signature. On
success the dependency returns the resolved key record and has already
logged the call to api_usage; on failure it raises an HTTPException with a
FHIR OperationOutcome body (see app/fhir_common.py) so a v1 API failure
looks like a FHIR failure, not a generic REST error.
"""
from typing import Any, Callable, Dict, Optional

from fastapi import Header, HTTPException, Request

from app import apikeys
from app.fhir_common import operation_outcome


def require_api_key(required_scope: Optional[str] = None) -> Callable[..., Dict[str, Any]]:
    def _dependency(
        request: Request,
        x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    ) -> Dict[str, Any]:
        if not x_api_key:
            raise HTTPException(
                status_code=401,
                detail=operation_outcome("error", "login", "Missing X-API-Key header. See /api/v1/api-keys to create one."),
            )

        try:
            key = apikeys.verify_key(x_api_key, required_scope=required_scope)
        except apikeys.InsufficientScopeError as e:
            raise HTTPException(status_code=403, detail=operation_outcome("error", "forbidden", str(e)))
        except apikeys.InvalidKeyError as e:
            raise HTTPException(status_code=401, detail=operation_outcome("error", "login", str(e)))

        try:
            apikeys.check_rate_limit(key["id"], key["rate_limit_per_minute"])
        except apikeys.RateLimitedError as e:
            raise HTTPException(status_code=429, detail=operation_outcome("error", "throttled", str(e)))

        apikeys.record_usage(key["id"], request.method, request.url.path)
        return key

    return _dependency
