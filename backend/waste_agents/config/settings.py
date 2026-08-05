"""
Centralized configuration for the Agricultural Waste Intelligence Agent.

All secrets are read from environment variables (see .env.example).
Nothing here should ever contain a hardcoded API key.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = two levels up from this file (config/settings.py -> project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """
    Application-wide settings, loaded from environment variables / .env file.

    Every field can be overridden by an environment variable of the same
    (uppercased) name, e.g. MISTRAL_API_KEY, TAVILY_API_KEY, etc.
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ------------------------------------------------------------------
    # LLM configuration
    # ------------------------------------------------------------------
    mistral_api_key: Optional[str] = Field(default=None, description="Mistral API key")
    mistral_model: str = Field(default="mistral-large-latest", description="Mistral model name used for extraction/reasoning")
    llm_provider: str = Field(default="mistral", description="Active LLM provider: 'mistral' (extensible to others)")
    llm_temperature: float = Field(default=0.0, description="Sampling temperature; 0.0 for maximum determinism")
    llm_max_retries: int = Field(default=5, description="Max retries on transient LLM API failures")
    llm_timeout_seconds: int = Field(default=60, description="Per-request timeout for LLM calls")
    llm_min_request_interval: float = Field(
        default=2.0,
        description=(
            "Minimum seconds between LLM requests, enforced across all threads. "
            "Free Mistral tiers allow roughly 1 request/second; raise this if you still see 429s."
        ),
    )
    llm_max_parallel_extractions: int = Field(
        default=2,
        description="How many extraction calls run concurrently. Higher is faster but risks rate limits.",
    )
    extraction_batch_size: int = Field(
        default=6,
        description=(
            "Sources packed into a single extraction call. Batching is what keeps a research pass "
            "fast without tripping rate limits: 30 sources at batch 6 is 5 calls instead of 30. "
            "Set to 1 to extract one source per call, which is slower but marginally more accurate."
        ),
    )
    extraction_batch_max_chars: int = Field(
        default=24000,
        description=(
            "Character budget per batch. A batch stops accepting sources once this is reached, so "
            "full-text sources batch in smaller groups than abstracts and prompts stay within context."
        ),
    )
    extraction_min_source_chars: int = Field(
        default=200,
        description="Sources shorter than this are skipped without an LLM call -- too thin to yield anything",
    )

    # ------------------------------------------------------------------
    # Web search configuration (general web)
    # ------------------------------------------------------------------
    web_search_provider: str = Field(default="tavily", description="Active web search provider: 'tavily' or 'serper'")
    tavily_api_key: Optional[str] = Field(default=None, description="Tavily API key")
    serper_api_key: Optional[str] = Field(default=None, description="Serper.dev API key")
    web_search_max_results: int = Field(default=5, description="Max results per web search query")

    # ------------------------------------------------------------------
    # Academic search configuration (no API key required)
    # ------------------------------------------------------------------
    semantic_scholar_api_key: Optional[str] = Field(
        default=None,
        description="Optional Semantic Scholar API key (raises rate limits; works without one)",
    )
    semantic_scholar_max_results: int = Field(default=8)
    crossref_mailto: Optional[str] = Field(
        default=None,
        description="Contact email sent to CrossRef 'polite pool' for higher rate limits (optional but recommended)",
    )
    crossref_max_results: int = Field(default=8)

    # ------------------------------------------------------------------
    # Embeddings / Vector store
    # ------------------------------------------------------------------
    embedding_model_name: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="Sentence-transformers model used to embed text for the vector store",
    )
    qdrant_url: Optional[str] = Field(
        default=None,
        description="Qdrant Cloud cluster URL, e.g. https://xxxx.aws.cloud.qdrant.io:6333",
    )
    qdrant_api_key: Optional[str] = Field(default=None, description="Qdrant Cloud API key")
    qdrant_collection_name: str = Field(default="agri_waste_knowledge")

    # ------------------------------------------------------------------
    # Storage paths
    # ------------------------------------------------------------------
    canonical_knowledge_path: str = Field(default=str(PROJECT_ROOT / "knowledge" / "canonical_knowledge.json"))
    documents_dir: str = Field(default=str(PROJECT_ROOT / "documents"))
    logs_dir: str = Field(default=str(PROJECT_ROOT / "logs"))

    # ------------------------------------------------------------------
    # Confidence / validation thresholds (mirrors prompt-level rules)
    # ------------------------------------------------------------------
    min_confidence_document: float = Field(default=0.80, description="Floor for DOCUMENT-sourced facts")
    max_confidence_model_knowledge: float = Field(default=0.70, description="Ceiling for LLM-internal-knowledge facts")
    min_confidence_to_store: float = Field(default=0.50, description="Absolute floor; below this, discard the fact")

    # ------------------------------------------------------------------
    # Research agent behaviour
    # ------------------------------------------------------------------
    max_search_queries_per_crop: int = Field(default=6, description="Cap on generated search queries per crop research pass")
    max_sources_per_query: int = Field(default=5, description="Cap on sources processed per search query")
    research_freshness_days: int = Field(
        default=90,
        description="If a crop's knowledge is older than this, the reasoner may trigger a fresh research pass",
    )

    # ------------------------------------------------------------------
    # App / logging
    # ------------------------------------------------------------------
    log_level: str = Field(default="INFO")
    app_env: str = Field(default="development")

    # ------------------------------------------------------------------
    # Observability (optional)
    # ------------------------------------------------------------------
    langsmith_tracing: bool = Field(
        default=False,
        description="Send pipeline traces to LangSmith. Requires LANGSMITH_API_KEY.",
    )
    langsmith_api_key: Optional[str] = Field(default=None, description="LangSmith API key")
    langsmith_project: str = Field(
        default="agri-waste-agent",
        description="LangSmith project name traces are grouped under",
    )
    langsmith_endpoint: Optional[str] = Field(
        default=None,
        description="Override for self-hosted or EU-region LangSmith instances",
    )

    ui_language: str = Field(
        default="en",
        description="Language for UI and chat answers. 'en' or 'fr'. "
                    "Data storage and validation always stay in English.",
    )


settings = Settings()


def ensure_directories() -> None:
    """Create all directories the app depends on, if they don't already exist."""
    for path_str in (
        settings.documents_dir,
        settings.logs_dir,
        str(Path(settings.canonical_knowledge_path).parent),
    ):
        Path(path_str).mkdir(parents=True, exist_ok=True)
