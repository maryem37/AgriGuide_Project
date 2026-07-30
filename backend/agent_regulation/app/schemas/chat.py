"""Schémas Pydantic pour les échanges de type question/réponse avec l'agent."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Question posée par l'utilisateur à l'agent."""

    question: str


class ChatResponse(BaseModel):
    """Réponse reformulée par l'agent."""

    answer: str
