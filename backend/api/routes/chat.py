from typing import Dict, List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from chatbot.orchestrator import answer_question

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: List[Dict[str, str]] = Field(default_factory=list)


@router.post("/chat")
def chat(request: ChatRequest):
    return answer_question(request.message, history=request.history)
