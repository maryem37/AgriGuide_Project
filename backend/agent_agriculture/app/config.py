"""
Central config. All values pull from environment variables so nothing
sensitive is hardcoded. Every default here points at a free/no-key
service per the project's academic constraint.

Ported from the standalone `agri-advisor-parcelle` prototype — field
names for external credentials are renamed to match the naming already
used in the repo's root `.env.example` (SENTINEL_HUB_* rather than the
prototype's COPERNICUS_*; both refer to the same OAuth client created
at dataspace.copernicus.eu, Sentinel Hub being the API surface exposed
by the Copernicus Data Space Ecosystem).
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent.parent  # backend/agent_agriculture/


class Settings(BaseSettings):
    # --- LLM (Mistral) ---
    mistral_api_key: str = ""  # free tier key from console.mistral.ai
    mistral_model: str = "mistral-small-latest"
    mistral_embed_model: str = "mistral-embed"

    # --- Fallback embeddings (used if no Mistral key / quota hit) ---
    local_embed_model: str = "intfloat/multilingual-e5-base"

    # --- Free geodata / API endpoints ---
    cadastre_api_base: str = "https://apicarto.ign.fr/api/cadastre"
    rpg_wfs_base: str = "https://data.geopf.fr/wfs/ows"
    soilgrids_base: str = "https://rest.isric.org/soilgrids/v2.0/properties/query"
    open_meteo_base: str = "https://api.open-meteo.com/v1/forecast"
    hal_api_base: str = "https://api.archives-ouvertes.fr/search/"

    # --- Storage ---
    chroma_persist_dir: str = str(_APP_DIR / "chroma_store")
    chroma_collection: str = "agri_rag_corpus"

    # --- Retrieval ---
    retrieval_top_k: int = 6
    chunk_min_tokens: int = 200
    chunk_max_tokens: int = 500
    chunk_overlap_ratio: float = 0.12

    # --- Satellite (Copernicus Data Space Ecosystem / Sentinel Hub — free account required) ---
    sentinel_hub_client_id: str = ""
    sentinel_hub_client_secret: str = ""

    # --- Phase B: DL crop classifier (BreizhCrops-pretrained TempCNN, fine-tuned) ---
    dl_checkpoint_path: str = str(_APP_DIR / "dl_checkpoints" / "tempcnn_finetuned.pth")
    dl_sequence_length: int = 45  # fixed input length the pretrained TempCNN architecture expects

    # --- Database (Postgres/PostGIS, shared with the other agents — see database/schema.sql) ---
    database_url: str = "postgresql://agriadvisor:changeme@localhost:5434/agriadvisor"

    # Reads the repo-root `.env` (shared secrets, e.g. MISTRAL_API_KEY /
    # SENTINEL_HUB_*) first, then an optional `backend/agent_agriculture/.env`
    # for service-local overrides — same file real OS env vars (Docker's
    # `env_file: .env`, see docker-compose.yml) already populate, so this is
    # just the local-dev-without-Docker equivalent. Listed as absolute paths
    # so this works regardless of the CWD the process is launched from.
    model_config = SettingsConfigDict(
        env_file=(str(_APP_DIR.parent.parent / ".env"), str(_APP_DIR / ".env")),
        extra="ignore",
    )


settings = Settings()
