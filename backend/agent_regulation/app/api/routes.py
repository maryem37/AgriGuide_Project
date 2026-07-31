"""Routes FastAPI exposées par l'agent de régulation.

Expose les endpoints permettant d'interroger l'agent (questions réglementaires,
recherche d'aides, remplissage/révision de documents).
"""

from fastapi import APIRouter

from app.agent.regulation_agent import RegulationAgent
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()
_agent = RegulationAgent()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Répond à une question de réglementation agricole via le RAG hybride."""
    answer = _agent.answer(request.question)
    return ChatResponse(answer=answer)
