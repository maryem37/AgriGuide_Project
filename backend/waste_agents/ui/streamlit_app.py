

"""
Streamlit UI for the Agricultural Waste Intelligence Agent.

Run with:
    streamlit run ui/streamlit_app.py

Pages:
    - Home
    - Knowledge Base Statistics (Dashboard)
    - Crop Search
    - Waste Search
    - Transformation Search
    - Question & Answer Chat
    - Knowledge Viewer
    - Upload Documents (secondary PDF path)
    - Extraction Logs
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import streamlit as st

# Ensure project root is importable when run via `streamlit run ui/streamlit_app.py`
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.knowledge_base import KnowledgeBaseAgent  # noqa: E402
from agents.reasoner import ReasonerAgent  # noqa: E402
from config.logging_config import InMemoryLogCapture, get_logger  # noqa: E402
from config.settings import settings  # noqa: E402
from models import Crop, Waste  # noqa: E402
from services.llm_service import LLMServiceError  # noqa: E402

logger = get_logger("ui")

st.set_page_config(
    page_title="Agri Waste Intelligence",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ======================================================================
# Internationalization (UI labels only -- retrieved knowledge and stored
# data always stay in English; see settings.ui_language)
# ======================================================================

LANG_CODES = ["en", "fr"]
LANG_NAMES = {"en": "English", "fr": "Français"}

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "sidebar_caption": "Autonomous agricultural waste research agent",
        "language_label": "Language",
        "nav_label": "Navigate",
        "page_home": "Home",
        "page_dashboard": "Knowledge Base Statistics",
        "page_crop_search": "Crop Search",
        "page_waste_search": "Waste Search",
        "page_transformation_search": "Transformation Search",
        "page_qa_chat": "Question & Answer Chat",
        "page_knowledge_viewer": "Knowledge Viewer",
        "page_upload_documents": "Upload Documents",
        "page_extraction_logs": "Extraction Logs",
        "dark_mode_label": "Dark mode",
        "missing_config": "Missing config:\n",
        "config_ok": "All required API keys configured.",
        "llm_caption": "LLM: {provider} ({model})",
        "websearch_caption": "Web search: {provider}",
        "tracing_caption": "🔍 Tracing: {project}",
        "home_title": "🌾 Agricultural Waste Intelligence Agent",
        "home_intro": (
            "This agent autonomously **researches, extracts, and organizes** scientific knowledge\n"
            "about agricultural waste valorization — what wastes a crop produces, their composition,\n"
            "how they can be transformed, and what products/applications result.\n\n"
            "Unlike a passive document Q&A tool, this agent **searches the web and academic\n"
            "databases itself** (Semantic Scholar, CrossRef, and general web search) to build and\n"
            "keep its knowledge base current. Uploading your own PDFs is supported as a secondary,\n"
            "optional input."
        ),
        "home_ask_title": "🔍 Ask a question",
        "home_ask_body": "Go to **{page}** to ask things like *\"What can Rice husk be transformed into?\"*",
        "home_research_title": "🌱 Research a crop",
        "home_research_body": "Go to **{page}**, type a crop name, and trigger autonomous research if it's not yet known.",
        "home_coverage_title": "📊 See coverage",
        "home_coverage_body": "Go to **{page}** for a live dashboard of what's been learned so far.",
        "home_examples_heading": "##### Example valorization chains",
        "dashboard_title": "📊 Knowledge Base Statistics",
        "stat_crops": "Crops",
        "stat_wastes": "Wastes",
        "stat_transformations": "Transformations",
        "stat_products": "Final Products",
        "dashboard_empty": "No crops in the knowledge base yet. Go to **{page}** to research your first crop.",
        "dashboard_crop_coverage_heading": "##### Crop coverage",
        "col_crop": "Crop",
        "col_scientific_name": "Scientific Name",
        "col_wastes": "Wastes",
        "col_references": "References",
        "col_avg_confidence": "Avg. Confidence",
        "col_last_research": "Last Research",
        "vector_store_caption": "Vector store: {count} indexed waste documents in collection '{collection}'.",
        "vector_store_unavailable": "Vector store status unavailable.",
        "crop_search_title": "🌱 Crop Search",
        "crop_name_label": "Crop name",
        "crop_name_placeholder": "e.g. Tomato, Banana, Rice, Coffee...",
        "research_button": "🔎 Research this crop",
        "research_button_plain": "Research this crop",
        "research_angle_label": "Optional research angle",
        "research_angle_placeholder": "e.g. 'composition', 'bioethanol production'",
        "researching_spinner": "Researching...",
        "research_success": "Found and synced {added} waste entries from {used}/{found} usable sources.",
        "research_warning": "No usable knowledge was extracted for this crop.",
        "research_issues_expander": "⚠️ {n} issue(s) during research",
        "crop_not_found": "No knowledge stored yet for '{crop}'. Click **{button}** above.",
        "aliases_caption": "Aliases: {aliases}",
        "crop_detail_caption": "{n} waste type(s) documented. Last research: {date}",
        "never_label": "never",
        "waste_details_expander": "Details — {name}",
        "label_description": "**Description:**",
        "label_plant_part": "**Plant part:**",
        "label_composition": "**Composition:**",
        "label_valorization_chain": "**Valorization chain:**",
        "label_final_products": "**Final products:**",
        "label_industrial_apps": "Industrial applications",
        "label_agri_apps": "Agricultural applications",
        "label_env_apps": "Environmental applications",
        "label_advantages": "**Advantages:**",
        "label_limitations": "**Limitations:**",
        "label_scientific_refs": "**Scientific references:**",
        "waste_search_title": "🍃 Waste Search",
        "waste_search_empty": "No wastes in the knowledge base yet.",
        "waste_search_label": "Search wastes by name",
        "waste_search_placeholder": "e.g. husk, peel, bagasse...",
        "results_caption": "{n} result(s)",
        "crop_caption": "Crop: {crop}",
        "transformation_search_title": "♻️ Transformation Search",
        "transformation_search_empty": "No transformations documented yet. Research some crops first.",
        "transformation_search_label": "Search by process or product",
        "transformation_search_placeholder": "e.g. biochar, compost, bioethanol...",
        "qa_chat_title": "💬 Question & Answer Chat",
        "qa_reference_expander": "{n} reference(s)",
        "qa_chat_placeholder": "Ask about agricultural waste, e.g. 'What can Banana leaves be transformed into?'",
        "qa_thinking": "Thinking...",
        "qa_thinking_research": "Thinking (may research '{crop}' live)...",
        "qa_live_research_caption": "🔎 Triggered a live research pass to answer this.",
        "compare_heading": "##### Compare two crops",
        "crop_a_label": "Crop A",
        "crop_b_label": "Crop B",
        "compare_button": "Compare",
        "compare_spinner": "Comparing {a} and {b}...",
        "knowledge_viewer_title": "📚 Knowledge Viewer",
        "knowledge_viewer_empty": "Knowledge base is empty.",
        "download_button": "⬇️ Download canonical_knowledge.json",
        "select_crop_label": "Select a crop to inspect raw JSON",
        "upload_title": "📄 Upload Documents (secondary source)",
        "upload_caption": (
            "PDFs are an optional, secondary input. The agent's primary knowledge source is "
            "autonomous web and academic research (see **{page}**)."
        ),
        "upload_file_label": "Upload a scientific PDF",
        "upload_crop_label": "Crop this document is about (required)",
        "upload_crop_placeholder": "e.g. Tomato",
        "upload_button": "Process PDF",
        "upload_spinner": "Processing PDF...",
        "upload_success": "Extracted and synced {n} waste entries from the PDF.",
        "upload_warning": "No usable knowledge extracted from this PDF.",
        "upload_issues_expander": "⚠️ {n} issue(s)",
        "logs_title": "🪵 Extraction Logs",
        "logs_empty": "No logs yet. Perform a research or extraction action to see logs here.",
        "logs_caption": "Showing last {n} log entries (most recent last).",
    },
    "fr": {
        "sidebar_caption": "Agent de recherche autonome sur les déchets agricoles",
        "language_label": "Langue",
        "nav_label": "Navigation",
        "page_home": "Accueil",
        "page_dashboard": "Statistiques de la base de connaissances",
        "page_crop_search": "Recherche de culture",
        "page_waste_search": "Recherche de déchet",
        "page_transformation_search": "Recherche de transformation",
        "page_qa_chat": "Chat questions-réponses",
        "page_knowledge_viewer": "Visualiseur de connaissances",
        "page_upload_documents": "Téléverser des documents",
        "page_extraction_logs": "Journaux d'extraction",
        "dark_mode_label": "Mode sombre",
        "missing_config": "Configuration manquante :\n",
        "config_ok": "Toutes les clés API requises sont configurées.",
        "llm_caption": "LLM : {provider} ({model})",
        "websearch_caption": "Recherche web : {provider}",
        "tracing_caption": "🔍 Traçage : {project}",
        "home_title": "🌾 Agent d'intelligence sur les déchets agricoles",
        "home_intro": (
            "Cet agent **recherche, extrait et organise** de manière autonome des connaissances\n"
            "scientifiques sur la valorisation des déchets agricoles — quels déchets une culture\n"
            "produit, leur composition, comment ils peuvent être transformés, et quels produits/\n"
            "applications en résultent.\n\n"
            "Contrairement à un outil passif de questions-réponses documentaires, cet agent\n"
            "**effectue lui-même des recherches sur le web et dans les bases académiques**\n"
            "(Semantic Scholar, CrossRef, et recherche web générale) pour construire et maintenir\n"
            "sa base de connaissances à jour. Le téléversement de vos propres PDF est pris en\n"
            "charge comme source secondaire, optionnelle."
        ),
        "home_ask_title": "🔍 Poser une question",
        "home_ask_body": "Allez dans **{page}** pour poser des questions comme *« En quoi la balle de riz (Rice Husk) peut-elle être transformée ? »*",
        "home_research_title": "🌱 Rechercher une culture",
        "home_research_body": "Allez dans **{page}**, saisissez un nom de culture, et déclenchez une recherche autonome si elle n'est pas encore connue.",
        "home_coverage_title": "📊 Voir la couverture",
        "home_coverage_body": "Allez dans **{page}** pour un tableau de bord en direct de ce qui a été appris jusqu'à présent.",
        "home_examples_heading": "##### Exemples de chaînes de valorisation",
        "dashboard_title": "📊 Statistiques de la base de connaissances",
        "stat_crops": "Cultures",
        "stat_wastes": "Déchets",
        "stat_transformations": "Transformations",
        "stat_products": "Produits finaux",
        "dashboard_empty": "Aucune culture dans la base de connaissances pour l'instant. Allez dans **{page}** pour rechercher votre première culture.",
        "dashboard_crop_coverage_heading": "##### Couverture par culture",
        "col_crop": "Culture",
        "col_scientific_name": "Nom scientifique",
        "col_wastes": "Déchets",
        "col_references": "Références",
        "col_avg_confidence": "Confiance moy.",
        "col_last_research": "Dernière recherche",
        "vector_store_caption": "Base vectorielle : {count} documents de déchets indexés dans la collection « {collection} ».",
        "vector_store_unavailable": "Statut de la base vectorielle indisponible.",
        "crop_search_title": "🌱 Recherche de culture",
        "crop_name_label": "Nom de la culture",
        "crop_name_placeholder": "ex. Tomate, Banane, Riz, Café...",
        "research_button": "🔎 Rechercher cette culture",
        "research_button_plain": "Rechercher cette culture",
        "research_angle_label": "Angle de recherche optionnel",
        "research_angle_placeholder": "ex. « composition », « production de bioéthanol »",
        "researching_spinner": "Recherche en cours...",
        "research_success": "{added} entrées de déchets trouvées et synchronisées à partir de {used}/{found} sources utilisables.",
        "research_warning": "Aucune connaissance utilisable n'a été extraite pour cette culture.",
        "research_issues_expander": "⚠️ {n} problème(s) pendant la recherche",
        "crop_not_found": "Aucune connaissance enregistrée pour « {crop} » pour l'instant. Cliquez sur **{button}** ci-dessus.",
        "aliases_caption": "Alias : {aliases}",
        "crop_detail_caption": "{n} type(s) de déchet documenté(s). Dernière recherche : {date}",
        "never_label": "jamais",
        "waste_details_expander": "Détails — {name}",
        "label_description": "**Description :**",
        "label_plant_part": "**Partie de la plante :**",
        "label_composition": "**Composition :**",
        "label_valorization_chain": "**Chaîne de valorisation :**",
        "label_final_products": "**Produits finaux :**",
        "label_industrial_apps": "Applications industrielles",
        "label_agri_apps": "Applications agricoles",
        "label_env_apps": "Applications environnementales",
        "label_advantages": "**Avantages :**",
        "label_limitations": "**Limites :**",
        "label_scientific_refs": "**Références scientifiques :**",
        "waste_search_title": "🍃 Recherche de déchet",
        "waste_search_empty": "Aucun déchet dans la base de connaissances pour l'instant.",
        "waste_search_label": "Rechercher un déchet par nom",
        "waste_search_placeholder": "ex. balle, épluchure, bagasse...",
        "results_caption": "{n} résultat(s)",
        "crop_caption": "Culture : {crop}",
        "transformation_search_title": "♻️ Recherche de transformation",
        "transformation_search_empty": "Aucune transformation documentée pour l'instant. Recherchez d'abord des cultures.",
        "transformation_search_label": "Rechercher par procédé ou produit",
        "transformation_search_placeholder": "ex. biochar, compost, bioéthanol...",
        "qa_chat_title": "💬 Chat questions-réponses",
        "qa_reference_expander": "{n} référence(s)",
        "qa_chat_placeholder": "Posez une question sur les déchets agricoles, ex. « En quoi les feuilles de banane peuvent-elles être transformées ? »",
        "qa_thinking": "Réflexion en cours...",
        "qa_thinking_research": "Réflexion en cours (peut rechercher « {crop} » en direct)...",
        "qa_live_research_caption": "🔎 Une recherche en direct a été déclenchée pour répondre à cette question.",
        "compare_heading": "##### Comparer deux cultures",
        "crop_a_label": "Culture A",
        "crop_b_label": "Culture B",
        "compare_button": "Comparer",
        "compare_spinner": "Comparaison de {a} et {b}...",
        "knowledge_viewer_title": "📚 Visualiseur de connaissances",
        "knowledge_viewer_empty": "La base de connaissances est vide.",
        "download_button": "⬇️ Télécharger canonical_knowledge.json",
        "select_crop_label": "Sélectionnez une culture pour inspecter le JSON brut",
        "upload_title": "📄 Téléverser des documents (source secondaire)",
        "upload_caption": (
            "Les PDF sont une source secondaire et optionnelle. La source principale de "
            "connaissances de l'agent est la recherche autonome sur le web et académique "
            "(voir **{page}**)."
        ),
        "upload_file_label": "Téléverser un PDF scientifique",
        "upload_crop_label": "Culture concernée par ce document (obligatoire)",
        "upload_crop_placeholder": "ex. Tomate",
        "upload_button": "Traiter le PDF",
        "upload_spinner": "Traitement du PDF en cours...",
        "upload_success": "{n} entrées de déchets extraites et synchronisées à partir du PDF.",
        "upload_warning": "Aucune connaissance utilisable extraite de ce PDF.",
        "upload_issues_expander": "⚠️ {n} problème(s)",
        "logs_title": "🪵 Journaux d'extraction",
        "logs_empty": "Aucun journal pour l'instant. Effectuez une recherche ou une extraction pour voir les journaux ici.",
        "logs_caption": "Affichage des {n} dernières entrées de journal (les plus récentes en dernier).",
    },
}


def get_ui_language() -> str:
    lang = st.session_state.get("ui_language")
    if lang not in STRINGS:
        lang = settings.ui_language.lower() if settings.ui_language.lower() in STRINGS else "en"
    return lang


def t(key: str, **kwargs) -> str:
    lang = get_ui_language()
    template = STRINGS.get(lang, STRINGS["en"]).get(key, STRINGS["en"].get(key, key))
    return template.format(**kwargs) if kwargs else template


PAGE_DEFS = [
    ("home", "page_home"),
    ("dashboard", "page_dashboard"),
    ("crop_search", "page_crop_search"),
    ("waste_search", "page_waste_search"),
    ("transformation_search", "page_transformation_search"),
    ("qa_chat", "page_qa_chat"),
    ("knowledge_viewer", "page_knowledge_viewer"),
    ("upload_documents", "page_upload_documents"),
    ("extraction_logs", "page_extraction_logs"),
]


# ======================================================================
# Cached singletons
# ======================================================================

@st.cache_resource
def get_kb_agent() -> KnowledgeBaseAgent:
    return KnowledgeBaseAgent()


@st.cache_resource
def get_reasoner_agent() -> ReasonerAgent:
    return ReasonerAgent()


@st.cache_resource
def get_log_capture() -> InMemoryLogCapture:
    import logging

    capture = InMemoryLogCapture(capacity=500)
    logging.getLogger().addHandler(capture)
    return capture


# Attach the in-memory log capture as early as possible
get_log_capture()


# ======================================================================
# Search-time / display-time translation (French UI only)
#
# The knowledge base itself is always stored and matched in English; these
# helpers only translate what the user types (so it can be matched) and
# what result fields show (so they can be read). Binomial scientific/Latin
# species names and citations are never translated; everything else
# (names, composition, units, applications...) is.
# ======================================================================

TERM_TRANSLATION_SYSTEM_PROMPT = (
    "You translate a short search term (a crop or waste name, one to a few words) "
    "from French to English literally, word for word if needed.\n\n"
    "RULES\n"
    "1. Output ONLY the translated term. No question marks, no extra words, no explanation.\n"
    "2. Do NOT turn it into a question or a sentence, even if it looks incomplete on its own.\n"
    "3. If the term is already in English, or you don't recognize it, return it unchanged.\n"
    "4. Preserve scientific/Latin names, acronyms, and numbers as-is."
)

TERM_TRANSLATION_USER_PROMPT = "Term: {term}\n\nTranslate to English. Output only the translated term, nothing else."


def translate_search_term(text: str) -> str:
    """Best-effort FR->EN translation of a search box value."""
    text = (text or "").strip()
    if not text or get_ui_language() != "fr":
        return text
    return _translate_term_cached(text)


@st.cache_data(show_spinner=False)
def _translate_term_cached(text: str) -> str:
    try:
        llm = get_reasoner_agent().llm_service
        translated = llm.complete(
            TERM_TRANSLATION_SYSTEM_PROMPT,
            TERM_TRANSLATION_USER_PROMPT.format(term=text),
            max_tokens=30,
        ).strip()
        return translated or text
    except LLMServiceError:
        return text


def translate_display_map(texts: list[str]) -> dict[str, str]:
    """Best-effort batch EN->FR translation for a set of short result
    fragments (names, descriptions, applications...). Returns {} in
    English mode, or on translation failure -- callers fall back to the
    original text via dict.get(text, text)."""
    if get_ui_language() != "fr":
        return {}
    unique = tuple(sorted({t for t in texts if t}))
    if not unique:
        return {}
    translated = _translate_batch_cached(unique)
    return dict(zip(unique, translated))


_BATCH_TRANSLATION_SYSTEM_PROMPT = (
    "You translate short agricultural-waste text fragments from English to French, "
    "for display in a search-results UI. This includes waste/product names, chemical "
    "compound/composition names, and units where a French term exists "
    "(e.g. 'Rice Husk' -> 'Balle de riz', 'Ash content' -> \"Teneur en cendres\").\n"
    "RULES\n"
    "1. Return ONLY a JSON array of strings: one translation per input fragment, "
    "same order, same length as the input. No explanation, no markdown fences.\n"
    "2. NEVER translate binomial scientific/Latin species names (e.g. 'Oryza sativa') "
    "-- copy them unchanged. A symbol or abbreviation with no French equivalent "
    "(e.g. '%', 'mg/kg') should also be copied unchanged.\n"
    "3. Keep meaning and register faithful to the source; do not add or omit detail."
)


def _translate_fragments(texts: tuple[str, ...]) -> tuple[str, ...]:
    """Translate a batch of fragments EN->FR in one LLM call. If the batch
    fails (truncated/invalid JSON -- e.g. too many or too long fragments for
    the token budget), split it in half and retry each half, so a handful of
    long fragments can't sink the translation of an entire card back to
    English."""
    if not texts:
        return texts
    numbered = "\n".join(f"{i + 1}. {frag}" for i, frag in enumerate(texts))
    user = f"Fragments:\n{numbered}\n\nReturn a JSON array of exactly {len(texts)} French translations, same order."
    try:
        llm = get_reasoner_agent().llm_service
        raw = llm.complete(_BATCH_TRANSLATION_SYSTEM_PROMPT, user, max_tokens=4000).strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
        if isinstance(parsed, list) and len(parsed) == len(texts):
            return tuple(str(x) for x in parsed)
    except (LLMServiceError, ValueError, json.JSONDecodeError):
        pass
    if len(texts) == 1:
        return texts
    mid = len(texts) // 2
    return _translate_fragments(texts[:mid]) + _translate_fragments(texts[mid:])


@st.cache_data(show_spinner=False)
def _translate_batch_cached(texts: tuple[str, ...]) -> tuple[str, ...]:
    return _translate_fragments(texts)


# ======================================================================
# Theme / styling
# ======================================================================

def inject_css(dark_mode: bool) -> None:
    if dark_mode:
        bg, card_bg, text, accent, border = "#0e1117", "#1a1d24", "#e8eaed", "#7fd858", "#2c303a"
    else:
        bg, card_bg, text, accent, border = "#fafaf7", "#ffffff", "#1a1a1a", "#2e7d32", "#e0e0d8"

    st.markdown(
        f"""
        <style>
        .stApp {{ background-color: {bg}; color: {text}; }}
        .metric-card {{
            background-color: {card_bg};
            border: 1px solid {border};
            border-radius: 10px;
            padding: 1.2rem;
            text-align: center;
        }}
        .metric-value {{ font-size: 2rem; font-weight: 700; color: {accent}; }}
        .metric-label {{ font-size: 0.85rem; opacity: 0.7; }}
        .waste-card {{
            background-color: {card_bg};
            border: 1px solid {border};
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 0.8rem;
        }}
        .confidence-badge {{
            display: inline-block;
            padding: 0.15rem 0.6rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            background-color: {accent}22;
            color: {accent};
        }}
        .chain-arrow {{ opacity: 0.5; margin: 0 0.4rem; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ======================================================================
# Sidebar navigation
# ======================================================================

def render_sidebar() -> tuple[str, bool]:
    with st.sidebar:
        st.markdown("## 🌾 Agri Waste Intelligence")

        default_lang = settings.ui_language.lower() if settings.ui_language.lower() in LANG_CODES else "en"
        current_lang = st.session_state.get("ui_language", default_lang)
        lang = st.selectbox(
            t("language_label"),
            options=LANG_CODES,
            index=LANG_CODES.index(current_lang),
            format_func=lambda code: LANG_NAMES[code],
            key="ui_language",
        )
        settings.ui_language = lang

        st.caption(t("sidebar_caption"))
        page_keys = [k for k, _ in PAGE_DEFS]
        label_by_key = {k: t(label_key) for k, label_key in PAGE_DEFS}
        page = st.radio(
            t("nav_label"),
            page_keys,
            format_func=lambda k: label_by_key[k],
            label_visibility="collapsed",
        )
        st.divider()
        dark_mode = st.toggle(t("dark_mode_label"), value=True)
        st.divider()

        missing = []
        if not settings.mistral_api_key:
            missing.append("MISTRAL_API_KEY")
        if settings.web_search_provider == "tavily" and not settings.tavily_api_key:
            missing.append("TAVILY_API_KEY")
        if settings.web_search_provider == "serper" and not settings.serper_api_key:
            missing.append("SERPER_API_KEY")

        if missing:
            st.warning(t("missing_config") + "\n".join(f"- `{m}`" for m in missing))
        else:
            st.success(t("config_ok"))

        st.caption(t("llm_caption", provider=settings.llm_provider, model=settings.mistral_model))
        st.caption(t("websearch_caption", provider=settings.web_search_provider))

        from services.tracing_service import is_tracing_enabled

        if is_tracing_enabled():
            st.caption(t("tracing_caption", project=settings.langsmith_project))

    return page, dark_mode


# ======================================================================
# Pages
# ======================================================================

def page_home() -> None:
    st.title(t("home_title"))
    st.markdown(t("home_intro"))

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"#### {t('home_ask_title')}")
        st.markdown(t("home_ask_body", page=t("page_qa_chat")))
    with col2:
        st.markdown(f"#### {t('home_research_title')}")
        st.markdown(t("home_research_body", page=t("page_crop_search")))
    with col3:
        st.markdown(f"#### {t('home_coverage_title')}")
        st.markdown(t("home_coverage_body", page=t("page_dashboard")))

    st.divider()
    st.markdown(t("home_examples_heading"))
    examples = [
        ["Rice Husk", "Biochar", "Activated Carbon", "Water Filtration"],
        ["Corn Stover", "Bioethanol", "Renewable Fuel"],
        ["Banana Leaves", "Compost", "Organic Fertilizer"],
        ["Sugarcane Bagasse", "Cellulose", "Paper", "Packaging"],
        ["Coffee Husk", "Biochar", "Soil Amendment"],
    ]
    for chain in examples:
        st.markdown(
            " <span class='chain-arrow'>→</span> ".join(f"**{step}**" for step in chain),
            unsafe_allow_html=True,
        )


def page_dashboard() -> None:
    st.title(t("dashboard_title"))
    kb_agent = get_kb_agent()
    kb = kb_agent.get_knowledge_base()
    stats = kb.stats()

    cols = st.columns(4)
    labels_values = [
        (t("stat_crops"), stats["num_crops"]),
        (t("stat_wastes"), stats["num_wastes"]),
        (t("stat_transformations"), stats["num_transformations"]),
        (t("stat_products"), stats["num_products"]),
    ]
    for col, (label, value) in zip(cols, labels_values):
        with col:
            st.markdown(
                f"<div class='metric-card'><div class='metric-value'>{value}</div>"
                f"<div class='metric-label'>{label}</div></div>",
                unsafe_allow_html=True,
            )

    st.divider()

    if not kb.crops:
        st.info(t("dashboard_empty", page=t("page_crop_search")))
        return

    st.markdown(t("dashboard_crop_coverage_heading"))
    rows = []
    for crop in kb.crops:
        n_refs = sum(len(w.references) for w in crop.wastes)
        avg_conf = (
            sum(w.confidence for w in crop.wastes) / len(crop.wastes) if crop.wastes else 0.0
        )
        rows.append(
            {
                t("col_crop"): crop.name,
                t("col_scientific_name"): crop.scientific_name or "—",
                t("col_wastes"): len(crop.wastes),
                t("col_references"): n_refs,
                t("col_avg_confidence"): round(avg_conf, 2),
                t("col_last_research"): (crop.last_research_at or "—")[:10],
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

    try:
        vector_count = kb_agent.vector_store.count()
        st.caption(t("vector_store_caption", count=vector_count, collection=settings.qdrant_collection_name))
    except Exception:  # noqa: BLE001
        st.caption(t("vector_store_unavailable"))


def page_crop_search() -> None:
    st.title(t("crop_search_title"))
    kb_agent = get_kb_agent()

    crop_name = st.text_input(t("crop_name_label"), placeholder=t("crop_name_placeholder"))
    col1, col2 = st.columns([1, 3])
    with col1:
        research_btn = st.button(t("research_button"), type="primary", disabled=not crop_name)
    with col2:
        angle = st.text_input(t("research_angle_label"), placeholder=t("research_angle_placeholder"))

    search_name = translate_search_term(crop_name)

    if research_btn and crop_name:
        progress_bar = st.progress(0.0)
        status_text = st.empty()

        def progress_cb(msg: str, frac: float) -> None:
            progress_bar.progress(min(frac, 1.0))
            status_text.text(msg)

        with st.spinner(t("researching_spinner")):
            summary = kb_agent.research_and_sync_crop(search_name, angle=angle, progress_cb=progress_cb)

        if summary.wastes_added_or_updated > 0:
            st.success(
                t(
                    "research_success",
                    added=summary.wastes_added_or_updated,
                    used=summary.sources_used,
                    found=summary.sources_found,
                )
            )
        else:
            st.warning(t("research_warning"))
        if summary.errors:
            with st.expander(t("research_issues_expander", n=len(summary.errors))):
                for err in summary.errors:
                    st.text(f"- {err}")

    st.divider()

    if crop_name:
        crop = kb_agent.get_crop(search_name)
        if crop:
            render_crop_detail(crop)
        else:
            st.info(t("crop_not_found", crop=crop_name, button=t("research_button_plain")))


def render_crop_detail(crop: Crop) -> None:
    st.subheader(f"{crop.name}" + (f"  _{crop.scientific_name}_" if crop.scientific_name else ""))
    if crop.aliases:
        st.caption(t("aliases_caption", aliases=", ".join(crop.aliases)))
    last_research = (crop.last_research_at or t("never_label"))[:19]
    st.caption(t("crop_detail_caption", n=len(crop.wastes), date=last_research))

    for waste in sorted(crop.wastes, key=lambda w: -w.confidence):
        render_waste_card(waste)


def render_waste_card(waste: Waste) -> None:
    waste_name = waste.canonical_name or waste.name
    translatable = [waste_name]
    if waste.description:
        translatable.append(waste.description)
    if waste.plant_part:
        translatable.append(waste.plant_part)
    for c in waste.composition:
        translatable.append(c.component)
        if c.unit:
            translatable.append(c.unit)
    for tr in waste.transformations:
        translatable.append(tr.input_waste)
        translatable.append(tr.process)
        translatable.append(tr.output_product)
        if tr.description:
            translatable.append(tr.description)
    translatable.extend(waste.final_products)
    for apps in (waste.industrial_applications, waste.agricultural_applications, waste.environmental_applications):
        translatable.extend(a.name for a in apps)
    translatable.extend(waste.advantages)
    translatable.extend(waste.limitations)
    tr_map = translate_display_map(translatable)

    def d(text: str) -> str:
        return tr_map.get(text, text) if text else text

    display_name = d(waste_name)

    with st.container():
        st.markdown(
            f"<div class='waste-card'>"
            f"<b>{display_name}</b> "
            f"<span class='confidence-badge'>{waste.confidence:.2f} · {waste.evidence_strength.value}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        with st.expander(t("waste_details_expander", name=display_name)):
            if waste.description:
                st.markdown(f"{t('label_description')} {d(waste.description)}")
            if waste.plant_part:
                st.markdown(f"{t('label_plant_part')} {d(waste.plant_part)}")
            if waste.composition:
                st.markdown(t("label_composition"))
                for c in waste.composition:
                    st.markdown(f"- {d(c.component)}: {c.value}{d(c.unit) if c.unit else ''}")
            if waste.transformations:
                st.markdown(t("label_valorization_chain"))
                for tr in waste.transformations:
                    st.markdown(
                        f"- {d(tr.input_waste)} → **{d(tr.process)}** → {d(tr.output_product)}"
                        + (f" _{d(tr.description)}_" if tr.description else "")
                    )
            if waste.final_products:
                st.markdown(f"{t('label_final_products')} " + ", ".join(d(p) for p in waste.final_products))
            for label_key, apps in (
                ("label_industrial_apps", waste.industrial_applications),
                ("label_agri_apps", waste.agricultural_applications),
                ("label_env_apps", waste.environmental_applications),
            ):
                if apps:
                    st.markdown(f"**{t(label_key)}:** " + ", ".join(d(a.name) for a in apps))
            if waste.advantages:
                st.markdown(f"{t('label_advantages')} " + ", ".join(d(a) for a in waste.advantages))
            if waste.limitations:
                st.markdown(f"{t('label_limitations')} " + ", ".join(d(a) for a in waste.limitations))
            if waste.references:
                st.markdown(t("label_scientific_refs"))
                for ref in waste.references:
                    label = ref.short_citation()
                    if ref.url:
                        st.markdown(f"- [{label}]({ref.url})")
                    else:
                        st.markdown(f"- {label}")


def page_waste_search() -> None:
    st.title(t("waste_search_title"))
    kb_agent = get_kb_agent()
    kb = kb_agent.get_knowledge_base()

    all_wastes = [(crop, w) for crop in kb.crops for w in crop.wastes]
    if not all_wastes:
        st.info(t("waste_search_empty"))
        return

    query = st.text_input(t("waste_search_label"), placeholder=t("waste_search_placeholder"))
    search_query = translate_search_term(query)
    filtered = [
        (crop, w)
        for crop, w in all_wastes
        if not search_query or search_query.lower() in (w.canonical_name or w.name).lower()
    ]
    st.caption(t("results_caption", n=len(filtered)))
    for crop, waste in filtered:
        st.caption(t("crop_caption", crop=crop.name))
        render_waste_card(waste)


def page_transformation_search() -> None:
    st.title(t("transformation_search_title"))
    kb_agent = get_kb_agent()
    kb = kb_agent.get_knowledge_base()

    all_transformations = [
        (crop, waste, tr) for crop in kb.crops for waste in crop.wastes for tr in waste.transformations
    ]
    if not all_transformations:
        st.info(t("transformation_search_empty"))
        return

    query = st.text_input(t("transformation_search_label"), placeholder=t("transformation_search_placeholder"))
    filtered = [
        (crop, waste, tr)
        for crop, waste, tr in all_transformations
        if not query
        or query.lower() in tr.process.lower()
        or query.lower() in tr.output_product.lower()
    ]
    st.caption(t("results_caption", n=len(filtered)))

    translatable = []
    for _, _, tr in filtered:
        translatable.extend([tr.input_waste, tr.process, tr.output_product])
        if tr.description:
            translatable.append(tr.description)
    tr_map = translate_display_map(translatable)

    def d(text: str) -> str:
        return tr_map.get(text, text) if text else text

    for crop, waste, tr in filtered:
        st.markdown(
            f"**{crop.name} / {waste.canonical_name or waste.name}**: "
            f"{d(tr.input_waste)} → **{d(tr.process)}** → {d(tr.output_product)} "
            f"<span class='confidence-badge'>{tr.confidence:.2f}</span>",
            unsafe_allow_html=True,
        )
        if tr.description:
            st.caption(d(tr.description))


def page_qa_chat() -> None:
    st.title(t("qa_chat_title"))
    reasoner = get_reasoner_agent()
    kb_agent = get_kb_agent()

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    known_crops = [c.name for c in kb_agent.get_knowledge_base().crops]

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("references"):
                with st.expander(t("qa_reference_expander", n=len(msg["references"]))):
                    for ref in msg["references"]:
                        st.caption(ref)

    question = st.chat_input(t("qa_chat_placeholder"))
    if question:
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        crop_hint = ReasonerAgent.extract_crop_hint(question, known_crops)

        with st.chat_message("assistant"):
            spinner_text = t("qa_thinking") if not crop_hint else t("qa_thinking_research", crop=crop_hint)
            with st.spinner(spinner_text):
                result = reasoner.answer(question, crop_hint=crop_hint)
            st.markdown(result.answer)
            if result.triggered_live_research:
                st.caption(t("qa_live_research_caption"))
            refs = [r.short_citation() for r in result.references]
            if refs:
                with st.expander(t("qa_reference_expander", n=len(refs))):
                    for r in refs:
                        st.caption(r)

        st.session_state.chat_history.append(
            {"role": "assistant", "content": result.answer, "references": refs}
        )

    st.divider()
    st.markdown(t("compare_heading"))
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        crop_a = st.text_input(t("crop_a_label"), key="cmp_a")
    with col2:
        crop_b = st.text_input(t("crop_b_label"), key="cmp_b")
    with col3:
        st.write("")
        st.write("")
        compare_btn = st.button(t("compare_button"), disabled=not (crop_a and crop_b))

    if compare_btn:
        with st.spinner(t("compare_spinner", a=crop_a, b=crop_b)):
            result = reasoner.compare_crops([crop_a, crop_b])
        st.markdown(result.answer)


def page_knowledge_viewer() -> None:
    st.title(t("knowledge_viewer_title"))
    kb_agent = get_kb_agent()
    kb = kb_agent.get_knowledge_base()

    if not kb.crops:
        st.info(t("knowledge_viewer_empty"))
        return

    st.download_button(
        t("download_button"),
        data=kb.model_dump_json(indent=2),
        file_name="canonical_knowledge.json",
        mime="application/json",
    )

    crop_names = [c.name for c in kb.crops]
    selected = st.selectbox(t("select_crop_label"), crop_names)
    crop = kb.find_crop(selected)
    if crop:
        st.json(crop.model_dump())


def page_upload_documents() -> None:
    st.title(t("upload_title"))
    st.caption(t("upload_caption", page=t("page_crop_search")))
    kb_agent = get_kb_agent()

    uploaded = st.file_uploader(t("upload_file_label"), type=["pdf"])
    crop_hint = st.text_input(t("upload_crop_label"), placeholder=t("upload_crop_placeholder"))

    if uploaded and crop_hint and st.button(t("upload_button"), type="primary"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded.getbuffer())
            tmp_path = tmp.name

        progress_bar = st.progress(0.0)
        status_text = st.empty()

        def progress_cb(msg: str, frac: float) -> None:
            progress_bar.progress(min(frac, 1.0))
            status_text.text(msg)

        with st.spinner(t("upload_spinner")):
            summary = kb_agent.sync_from_pdf(tmp_path, crop_hint, title_hint=uploaded.name, progress_cb=progress_cb)

        if summary.wastes_added_or_updated > 0:
            st.success(t("upload_success", n=summary.wastes_added_or_updated))
        else:
            st.warning(t("upload_warning"))
        if summary.errors:
            with st.expander(t("upload_issues_expander", n=len(summary.errors))):
                for err in summary.errors:
                    st.text(f"- {err}")


def page_extraction_logs() -> None:
    st.title(t("logs_title"))
    log_capture = get_log_capture()
    logs = log_capture.get_logs()

    if not logs:
        st.info(t("logs_empty"))
        return

    st.caption(t("logs_caption", n=len(logs)))
    st.code("\n".join(logs[-300:]), language="log")


# ======================================================================
# Main
# ======================================================================

def main() -> None:
    page, dark_mode = render_sidebar()
    inject_css(dark_mode)

    dispatch = {
        "home": page_home,
        "dashboard": page_dashboard,
        "crop_search": page_crop_search,
        "waste_search": page_waste_search,
        "transformation_search": page_transformation_search,
        "qa_chat": page_qa_chat,
        "knowledge_viewer": page_knowledge_viewer,
        "upload_documents": page_upload_documents,
        "extraction_logs": page_extraction_logs,
    }
    dispatch[page]()


if __name__ == "__main__":
    main()
