"""Interface Streamlit simple (thème agriculture) pour tester l'agent de régulation.

Se connecte directement à `RegulationAgent` (pas besoin de lancer l'API FastAPI).
Lancement : streamlit run interface_test/app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from app.agent.regulation_agent import RegulationAgent

EXAMPLE_QUESTIONS = [
    "Quel est le montant de l'aide ovine pour 2025 ?",
    "Quel est le montant de l'aide caprine pour 2025 ?",
    "Quelles nouvelles aides agricoles pour 2026 ?",
    "Quelles sont les conditions de la PAC pour les jeunes agriculteurs ?",
]

st.set_page_config(page_title="Assistant Réglementation Agricole", page_icon="🌾", layout="centered")

st.markdown(
    """
    <style>
    .stApp { background-color: #f4f7ee; }
    h1 { color: #2e5d34; }
    [data-testid="stChatMessage"] { border-radius: 12px; }

    /* Boules de questions suggérées */
    div[data-testid="stButton"] > button {
        border-radius: 999px;
        border: 1px solid #a8c58a;
        background-color: #e3ecd9;
        color: #2e5d34;
        padding: 0.5rem 1rem;
        font-size: 0.85rem;
        white-space: normal;
    }
    div[data-testid="stButton"] > button:hover {
        background-color: #2e5d34;
        border-color: #2e5d34;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🌾 Assistant de Régulation Agricole")
st.caption("Posez vos questions sur la réglementation, la PAC et les aides agricoles.")


@st.cache_resource(show_spinner="Initialisation de l'agent...")
def load_agent() -> RegulationAgent:
    return RegulationAgent()


agent = load_agent()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

pending_question = None

if not st.session_state.messages:
    st.markdown("**💡 Exemples de questions :**")
    cols = st.columns(2)
    for i, example in enumerate(EXAMPLE_QUESTIONS):
        if cols[i % 2].button(example, key=f"example_{i}", use_container_width=True):
            pending_question = example

typed_question = st.chat_input("Ex : Quel est le montant de l'aide ovine pour 2025 ?")
question = pending_question or typed_question

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Recherche en cours..."):
            answer = agent.answer(question)
        st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})

    if pending_question:
        st.rerun()
