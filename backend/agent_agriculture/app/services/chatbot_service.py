"""
Conversational assistant for the floating chat widget on the
Agriculture page. Two blended modes, decided per-question rather than
as a fixed toggle:

  1. General agricultural knowledge — grounded in the same Chroma RAG
     corpus the advisor report uses (app.services.rag_service).
  2. Questions about the currently selected parcel — grounded in
     ChatParcelContext, a snapshot of a prior /analyze response the
     frontend already has in memory (no second backend round-trip, no
     DB read).

Both grounding sources are simply included in the same prompt; the
model decides which is relevant to the actual question. Stateless on
the backend — the frontend resends the running message history each
call, same pattern as the parcel context.
"""
import asyncio
import json

from mistralai import Mistral

from app.config import settings
from app.hal_title_lookup import hal_id_from_filename, hal_url, offline_fallback_title
from app.models.schemas import ChatMessage, ChatParcelContext, ChatResponse, ChatSource
from app.services import rag_service

_client = Mistral(api_key=settings.mistral_api_key) if settings.mistral_api_key else None

# Keep prompt size bounded — only the most recent turns matter for a
# follow-up question; older context rarely changes the answer and
# just costs tokens.
_MAX_HISTORY_TURNS = 12
_RAG_TOP_K = 4

_SYSTEM_PROMPT = """Tu es l'assistant conversationnel d'AgriAdvisor, une \
plateforme d'aide à la décision pour les agriculteurs et nouveaux \
investisseurs agricoles en France. Tu réponds en français, de façon \
concise et directe, comme un conseiller agricole expérimenté — pas \
comme un moteur de recherche.

Tu reçois potentiellement deux sources de contexte avec chaque question :

1. "extraits_documentaires" — des passages d'un corpus documentaire \
(ARVALIS, Terres Inovia, ITB, HAL, etc.) pertinents pour une question \
agronomique générale. Utilise-les pour toute question de connaissance \
générale (pratiques culturales, réglementation technique, itinéraires \
techniques, etc.), et n'invente pas de chiffre ou de recommandation \
technique qui n'y figure pas — dis simplement que le corpus ne couvre \
pas ce point plutôt que d'estimer.

2. "parcelle_selectionnee" — les données réelles déjà calculées pour la \
parcelle actuellement sélectionnée par l'utilisateur sur la carte (sol, \
météo, végétation, cultures recommandées, rendement estimé, dose \
d'azote). Utilise ces données pour toute question portant sur "cette \
parcelle", "mon terrain", "ce sol", etc. Si ce contexte est absent, dis \
à l'utilisateur qu'aucune parcelle n'est actuellement sélectionnée et \
invite-le à en choisir une sur la carte s'il pose une question qui en \
dépend.

Ne mélange jamais les deux : un chiffre de la parcelle sélectionnée \
n'est pas une règle générale, et un extrait documentaire générique \
n'est pas une donnée mesurée sur cette parcelle précise. Si tu n'as ni \
document pertinent ni donnée de parcelle pour répondre avec certitude, \
dis-le clairement plutôt que de deviner.

Style de réponse — c'est le point le plus important : tu t'adresses à \
un agriculteur, pas à un collègue chercheur. Explique comme tu \
parlerais à quelqu'un dans un champ, pas comme un rapport technique.

- Phrases courtes. Une idée par phrase. Pas de sur-subordination.
- Zéro jargon non expliqué. Si un terme technique est nécessaire \
(ex. "CEC", "hydromorphie", "azote assimilable"), explique-le en \
quelques mots simples la première fois que tu l'utilises, dans la \
même phrase — pas dans un glossaire à part.
- Aucun chiffre ou fait technique perdu : tu peux être simple sans \
être vague. Garde chaque donnée précise (dose en kg/ha, pH, date, \
rendement) — reformule autour, jamais le chiffre lui-même.
- Rends-le concret : une comparaison, une image ou un exemple du \
quotidien agricole aide plus qu'une définition abstraite (ex. "un sol \
avec une bonne CEC, c'est un sol qui retient bien les engrais au lieu \
de les laisser filer avec la pluie").
- Structure seulement si ça aide vraiment à lire (une petite liste \
pour 3 conseils distincts, par exemple) — sinon écris en paragraphes \
courts et naturels, pas un rapport à puces.
- Va droit au but dans la première phrase, puis développe. Pas de \
longue mise en contexte avant la réponse.
- Ton chaleureux et engageant, jamais robotique ou scolaire — comme un \
bon conseiller de terrain qui a plaisir à expliquer, pas comme une \
notice."""


def _require_client():
    if _client is None:
        raise RuntimeError(
            "MISTRAL_API_KEY not set. Get a free key at console.mistral.ai "
            "or point config.py at a self-hosted open-weight Mistral endpoint."
        )


def _build_sources(chunks) -> list[ChatSource]:
    seen: set[str] = set()
    sources: list[ChatSource] = []
    for c in chunks:
        title = c.title or offline_fallback_title(c.source_document)
        url = c.url or hal_url(hal_id_from_filename(c.source_document))
        if url in seen:
            continue
        seen.add(url)
        sources.append(ChatSource(title=title, url=url))
    return sources


async def answer_question(
    question: str,
    history: list[ChatMessage],
    parcel_context: ChatParcelContext | None,
) -> ChatResponse:
    _require_client()

    # RAG retrieval is best-effort: an empty or unreachable corpus
    # should degrade to "no documentary context" rather than fail the
    # whole chat turn — general conversation and parcel-context
    # questions should still work without it.
    chunks = []
    try:
        chunks = rag_service.retrieve(question, top_k=_RAG_TOP_K)
    except Exception:
        chunks = []

    context_payload: dict = {}
    if chunks:
        context_payload["extraits_documentaires"] = [
            {"text": c.text, "source_document": c.source_document}
            for c in chunks
        ]
    if parcel_context is not None:
        context_payload["parcelle_selectionnee"] = parcel_context.model_dump(exclude_none=True)

    messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
    for turn in history[-_MAX_HISTORY_TURNS:]:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({
        "role": "user",
        "content": json.dumps(
            {"question": question, "contexte": context_payload},
            ensure_ascii=False,
        ),
    })

    resp = await asyncio.to_thread(
        _client.chat.complete,
        model=settings.mistral_model,
        temperature=0.3,
        messages=messages,
    )
    answer = resp.choices[0].message.content

    return ChatResponse(answer=answer, sources=_build_sources(chunks))
