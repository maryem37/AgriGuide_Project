"""Shared Groq chat configuration and RAG context formatting."""

import os
import time

from dotenv import load_dotenv
from groq import Groq


load_dotenv()

# Any current Groq-hosted model works here, e.g. "llama-3.3-70b-versatile",
# "llama-3.1-8b-instant", "mixtral-8x7b-32768" (if still available on your
# account), or "deepseek-r1-distill-llama-70b". Check https://console.groq.com/docs/models
# for the current list, since Groq periodically retires older models.
CHAT_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """Tu es AgriVision AI, un assistant d'analyse du marché agricole français.
Réponds en français, de façon claire et concise. Utilise uniquement le contexte
fourni pour les faits et les chiffres. Si le contexte ne permet pas de répondre,
dis-le explicitement plutôt que d'inventer une information. Cite les sources
disponibles dans le contexte lorsque c'est utile."""


def _get_groq_client() -> Groq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set. Add it to your .env file.")
    return Groq(api_key=api_key)


groq_client = _get_groq_client()


class RateLimitError(RuntimeError):
    """Raised when Groq still rejects a request after bounded retries."""


def complete_chat(**kwargs):
    """Complete a chat request, retrying only transient Groq rate limits.

    Accepts the same kwargs you'd pass to Mistral's chat.complete, with one
    difference: use `seed` instead of `random_seed` (Groq/OpenAI-style naming).
    """
    for attempt in range(3):
        try:
            return groq_client.chat.completions.create(**kwargs)
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            if status_code is None:
                status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if status_code != 429:
                raise

            if attempt == 2:
                raise RateLimitError(
                    "Groq is rate-limiting this API key. Wait a minute and try "
                    "again, or review the API key's quota and billing limits."
                ) from exc

            retry_after = None
            headers = getattr(getattr(exc, "response", None), "headers", None)
            if headers:
                retry_after = headers.get("retry-after")
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