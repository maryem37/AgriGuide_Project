"""
Reasoner agent.

Answers user questions by retrieving relevant Waste documents from the
vector store (built by KnowledgeBaseAgent) and asking the LLM to compose
an answer strictly grounded in that retrieved context. If retrieval
coverage looks too thin for the crop(s) mentioned in the question, it can
trigger a live research pass via KnowledgeBaseAgent before answering.
"""
from __future__ import annotations

import re
from typing import Optional

from agents.knowledge_base import KnowledgeBaseAgent
from config.logging_config import get_logger
from config.settings import settings
from models import ExtractionStatus, QAAnswer, Reference, SourceType
from prompts.qa_prompts import (
    COMPARISON_USER_PROMPT,
    QA_SYSTEM_PROMPT,
    QA_USER_PROMPT,
    QUERY_TRANSLATION_SYSTEM_PROMPT,
    QUERY_TRANSLATION_USER_PROMPT,
    answer_language_instruction,
)
from services.llm_service import LLMService, LLMServiceError, get_llm_service
from services.tracing_service import log_metadata, traced
from services.vector_store_service import VectorStoreService, get_vector_store

logger = get_logger(__name__)

MIN_HITS_FOR_CONFIDENT_ANSWER = 2


class ReasonerAgent:
    """Answers user questions via RAG over the knowledge base, with optional live research."""

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        vector_store: Optional[VectorStoreService] = None,
        kb_agent: Optional[KnowledgeBaseAgent] = None,
    ) -> None:
        self.llm_service = llm_service or get_llm_service()
        self.vector_store = vector_store or get_vector_store()
        self.kb_agent = kb_agent or KnowledgeBaseAgent()

    def _translate_query(self, question: str) -> str:
        """Translate question to English for vector search. Best-effort:
        on failure, returns the original so the search still runs."""
        if settings.ui_language.lower() == "en":
            return question
        try:
            translated = self.llm_service.complete(
                QUERY_TRANSLATION_SYSTEM_PROMPT,
                QUERY_TRANSLATION_USER_PROMPT.format(question=question),
                max_tokens=300,
            ).strip()
            return translated or question
        except LLMServiceError as e:
            logger.warning(
                "Query translation failed, using original: %s", e
            )
            return question

    @traced(name="answer_question")
    def answer(
        self,
        question: str,
        crop_hint: Optional[str] = None,
        allow_live_research: bool = True,
    ) -> QAAnswer:
        """Answer a free-form question, optionally triggering live research if coverage is thin."""
        search_query = self._translate_query(question)
        hits = self.vector_store.query(search_query, n_results=6, crop_filter=crop_hint)
        triggered_research = False

        if len(hits) < MIN_HITS_FOR_CONFIDENT_ANSWER and allow_live_research and crop_hint:
            logger.info("Insufficient coverage (%d hits) for '%s'; triggering live research.", len(hits), crop_hint)
            summary = self.kb_agent.research_and_sync_crop(crop_hint)
            triggered_research = True
            if summary.wastes_added_or_updated > 0:
                hits = self.vector_store.query(search_query, n_results=6, crop_filter=crop_hint)

        context_text, references = self._build_context(hits)
        research_note = (
            "A live research pass was triggered because existing knowledge base coverage was insufficient."
            if triggered_research
            else "No live research was triggered; answering from existing knowledge base."
        )

        user_prompt = QA_USER_PROMPT.format(
            question=question,
            context=context_text or "(no relevant context found in knowledge base)",
            research_note=research_note,
        )
        instruction = answer_language_instruction(settings.ui_language)
        if instruction:
            user_prompt = user_prompt + "\n\n" + instruction

        try:
            answer_text = self.llm_service.complete(QA_SYSTEM_PROMPT, user_prompt, max_tokens=1500)
        except LLMServiceError as e:
            logger.error("Reasoner LLM call failed: %s", e)
            return QAAnswer(
                answer="I couldn't generate an answer due to an LLM service error. Please try again.",
                status=ExtractionStatus.UNKNOWN,
                triggered_live_research=triggered_research,
            )

        status = ExtractionStatus.SUCCESS if hits else ExtractionStatus.UNKNOWN
        crop_names = sorted({h["metadata"].get("crop", "") for h in hits if h["metadata"].get("crop")})

        return QAAnswer(
            answer=answer_text.strip(),
            status=status,
            crop_names=crop_names,
            references=references,
            triggered_live_research=triggered_research,
        )

    def compare_crops(self, crops: list[str], allow_live_research: bool = True) -> QAAnswer:
        """Answer a comparison question across two or more crops."""
        all_hits = []
        for crop in crops:
            hits = self.vector_store.query(f"waste products of {crop}", n_results=5, crop_filter=crop)
            if len(hits) < MIN_HITS_FOR_CONFIDENT_ANSWER and allow_live_research:
                self.kb_agent.research_and_sync_crop(crop)
                hits = self.vector_store.query(f"waste products of {crop}", n_results=5, crop_filter=crop)
            all_hits.extend(hits)

        context_text, references = self._build_context(all_hits)
        user_prompt = COMPARISON_USER_PROMPT.format(
            crops=", ".join(crops),
            context=context_text or "(no relevant context found in knowledge base)",
        )
        instruction = answer_language_instruction(settings.ui_language)
        if instruction:
            user_prompt = user_prompt + "\n\n" + instruction

        try:
            answer_text = self.llm_service.complete(QA_SYSTEM_PROMPT, user_prompt, max_tokens=2000)
        except LLMServiceError as e:
            logger.error("Comparison LLM call failed: %s", e)
            return QAAnswer(
                answer="I couldn't generate a comparison due to an LLM service error. Please try again.",
                status=ExtractionStatus.UNKNOWN,
            )

        return QAAnswer(
            answer=answer_text.strip(),
            status=ExtractionStatus.SUCCESS if all_hits else ExtractionStatus.UNKNOWN,
            crop_names=crops,
            references=references,
        )

    def _build_context(self, hits: list[dict]) -> tuple[str, list[Reference]]:
        if not hits:
            return "", []

        blocks = []
        references = []
        for h in hits:
            meta = h["metadata"]
            blocks.append(f"[{meta.get('crop', '?')} / {meta.get('waste_name', '?')}]\n{h['document']}")
            references.append(
                Reference(
                    source_type=SourceType.WEB_PAGE,
                    title=f"{meta.get('crop', '')} - {meta.get('waste_name', '')}",
                    snippet=h["document"][:300],
                )
            )
        return "\n\n---\n\n".join(blocks), references

    @staticmethod
    def extract_crop_hint(question: str, known_crops: list[str]) -> Optional[str]:
        """Best-effort heuristic to spot a known crop name mentioned in a question."""
        q_lower = question.lower()
        for crop in known_crops:
            if re.search(rf"\b{re.escape(crop.lower())}\b", q_lower):
                return crop
        return None
