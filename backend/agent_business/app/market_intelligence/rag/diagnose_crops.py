"""Shared Mistral chat configuration and RAG context formatting."""

from __future__ import annotations

import os
import time

from dotenv import load_dotenv

load_dotenv()

CHAT_MODEL = "mistral-large-latest"

SYSTEM_PROMPT = """Tu es AgriVision AI, un assistant d'analyse du marché agricole français.
Réponds en français, de façon claire et concise. Utilise uniquement le contexte
fourni pour les faits et les chiffres. Si le contexte ne permet pas de répondre,
dis-le explicitement plutôt que d'inventer une information. Cite les sources
disponibles dans le contexte lorsque c'est utile."""

_mistral_client = None


class RateLimitError(RuntimeError):
    """Raised when Mistral still rejects a request after bounded retries."""


def _get_mistral_client():
    global _mistral_client
    if _mistral_client is not None:
        return _mistral_client
    from mistralai import Mistral

    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY not set. Add it to your .env file.")
    _mistral_client = Mistral(api_key=api_key)
    return _mistral_client


def complete_chat(**kwargs):
    """Complete a chat request, retrying only transient Mistral rate limits."""
    client = _get_mistral_client()
    for attempt in range(3):
        try:
            return client.chat.complete(**kwargs)
        except Exception as exc:
            if getattr(exc, "status_code", None) != 429:
                raise

            if attempt == 2:
                raise RateLimitError(
                    "Mistral is rate-limiting this API key. Wait a minute and try "
                    "again, or review the API key's quota and billing limits."
                ) from exc

            retry_after = getattr(exc, "headers", {}).get("retry-after")
            try:
                delay = min(float(retry_after), 15) if retry_after else 2 ** (attempt + 1)
            except (TypeError, ValueError):
                delay = 2 ** (attempt + 1)
            time.sleep(delay)


def build_context_block(hits: list[dict]) -> str:
    """Format retrieved Chroma chunks into a traceable chat context block."""
    if not hits:
        return "Aucun document pertinent n'a été trouvé."

    context_lines = []
    for index, hit in enumerate(hits, start=1):
        metadata = hit.get("metadata") or {}
        source = metadata.get("source", "source inconnue")
        location = ""
        if metadata.get("page") is not None:
            location = f", page {metadata['page']}"
        elif metadata.get("row") is not None:
            location = f", ligne {metadata['row']}"
        text = str(hit.get("text", "")).strip()
        context_lines.append(f"[{index}] Source : {source}{location}\n{text}")

    return "\n\n".join(context_lines)
