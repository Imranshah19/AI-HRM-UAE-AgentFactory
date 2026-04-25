"""
AI-HRMS — HR Chatbot API Router.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.ai.chatbot.engine import ChatResponse, get_chat_engine
from app.models.tenant import User

router = APIRouter(prefix="/ai/chat", tags=["AI — Chatbot"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ChatHistoryMessage(BaseModel):
    role:    str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message:              str
    conversation_history: list[ChatHistoryMessage] = []


class ChatResponseSchema(BaseModel):
    answer:            str
    data:              dict | None = None
    intent:            str
    sources:           list[str]
    suggested_actions: list[dict]
    confidence:        float

    model_config = ConfigDict(from_attributes=True)


class SuggestionsResponse(BaseModel):
    suggestions: list[str]
    role:        str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/", response_model=ChatResponseSchema)
async def chat(
    request: ChatRequest,
    db:      AsyncSession = Depends(get_db),
    current: User         = Depends(get_current_user),
):
    """
    Send a message to the HR AI assistant.
    Returns a structured response with answer, data, and suggested actions.
    """
    engine = get_chat_engine()

    # Build user context from authenticated user
    user_context = {
        "user_id":     str(current.id),
        "tenant_id":   str(current.tenant_id),
        "role":        current.role if hasattr(current, "role") else "employee",
        "employee_id": str(current.employee_id) if hasattr(current, "employee_id") and current.employee_id else None,
    }

    response: ChatResponse = await engine.answer(
        query=request.message,
        user_context=user_context,
        db=db,
    )

    return {
        "answer":            response.answer,
        "data":              response.data,
        "intent":            response.intent,
        "sources":           response.sources,
        "suggested_actions": response.suggested_actions,
        "confidence":        response.confidence,
    }


@router.get("/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(
    current: User = Depends(get_current_user),
):
    """
    Return suggested questions based on the user's role.
    """
    engine = get_chat_engine()
    role   = current.role if hasattr(current, "role") else "employee"
    return {
        "suggestions": engine.get_suggestions(role),
        "role":        role,
    }
