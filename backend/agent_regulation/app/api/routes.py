"""Routes FastAPI exposées par l'agent de régulation.

Expose les endpoints permettant d'interroger l'agent (questions réglementaires,
recherche d'aides, remplissage/révision de documents).
"""

import app.boot_encoding  # noqa: F401

from fastapi import APIRouter, HTTPException

from app.agent.regulation_agent import RegulationAgent
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()
_agent: RegulationAgent | None = None


def _get_agent() -> RegulationAgent:
    """Instancie l'agent à la première requête (après chargement du .env)."""
    global _agent
    if _agent is None:
        try:
            _agent = RegulationAgent()
        except ValueError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _agent


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Répond à une question de réglementation agricole via le RAG hybride."""
    try:
        answer = _get_agent().answer(request.question)
    except HTTPException:
        raise
    except Exception as exc:
        # Renvoie une erreur HTTP propre (avec en-têtes CORS) plutôt qu'un 500
        # non géré que le navigateur affiche souvent comme une erreur CORS.
        raise HTTPException(
            status_code=502,
            detail=f"Échec de l'appel à l'agent Régulation : {exc}",
        ) from exc
    return ChatResponse(answer=answer)
