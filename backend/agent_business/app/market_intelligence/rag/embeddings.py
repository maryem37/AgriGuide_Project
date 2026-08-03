"""Mistral embeddings for market RAG (no local torch model required)."""

from __future__ import annotations

import os
import time

from dotenv import load_dotenv

load_dotenv()

EMBED_MODEL = "mistral-embed"
_BATCH = 8
_client = None


def _client_mistral():
    global _client
    if _client is not None:
        return _client
    from mistralai import Mistral

    key = os.environ.get("MISTRAL_API_KEY")
    if not key:
        raise RuntimeError("MISTRAL_API_KEY required for market RAG embeddings.")
    _client = Mistral(api_key=key)
    return _client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts in small batches with basic 429 retry."""
    if not texts:
        return []
    client = _client_mistral()
    out: list[list[float]] = []
    for i in range(0, len(texts), _BATCH):
        batch = texts[i : i + _BATCH]
        for attempt in range(4):
            try:
                resp = client.embeddings.create(model=EMBED_MODEL, inputs=batch)
                out.extend([d.embedding for d in resp.data])
                break
            except Exception as exc:
                if getattr(exc, "status_code", None) != 429 or attempt == 3:
                    raise
                time.sleep(2 ** (attempt + 1))
        time.sleep(0.05)
    return out


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
