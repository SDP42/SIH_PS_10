"""
Voice / text assistant API — mounted under /api/v1/assistant.

Asking a question is read-only and open. Confirming a prepared action
writes clinical data, so it requires the same ABHA Demo Mode auth that
governance decisions and Bundle uploads already use — a spoken sentence
alone can never cause a write.
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app import assistant
from app.auth import require_demo_auth

router = APIRouter(prefix="/api/v1/assistant", tags=["Voice Assistant"])


class AskRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000, description="Transcribed speech or typed question")
    context_code: Optional[str] = Field(None, description="Code currently in view, for follow-ups like 'add this to the problem list'")


@router.post("/ask")
def ask(body: AskRequest) -> Dict[str, Any]:
    """
    Single entry point for voice and typed input alike — the browser does
    speech-to-text locally via the Web Speech API, so this only ever
    receives text and behaves identically either way.
    """
    return assistant.ask(body.text, context_code=body.context_code)


class ConfirmRequest(BaseModel):
    action: Dict[str, Any] = Field(..., description="The pending_action returned by /ask")


@router.post("/confirm")
def confirm(body: ConfirmRequest, operator: Dict[str, Any] = Depends(require_demo_auth)) -> Dict[str, Any]:
    """Executes a prepared action after explicit user confirmation. Requires auth."""
    actor = f"{operator.get('name')} ({operator.get('role')})"
    result = assistant.confirm_action(body.action, actor=actor)
    if not result.get("executed"):
        raise HTTPException(status_code=400, detail={"error": "ACTION_NOT_EXECUTED", "message": result.get("answer")})
    return result


@router.get("/capabilities")
def capabilities() -> Dict[str, Any]:
    """What the assistant can answer — used to populate on-screen example prompts."""
    return assistant.capabilities()


@router.post("/reload-knowledge-base")
def reload_kb(operator: Dict[str, Any] = Depends(require_demo_auth)) -> Dict[str, Any]:
    """
    Re-reads data/knowledge_base.json without restarting the service, so the
    answer set can be edited by someone who does not deploy code.
    """
    entries = assistant.load_knowledge_base(force=True)
    return {"reloaded": True, "entries": len(entries)}
