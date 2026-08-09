"""
app.py
------
AgriVision AI - unified entrypoint.

Merges two previously separate Streamlit apps into one flow:

  1. Market Intelligence  - free-form Q&A over the market RAG knowledge base
  2. Crop Ranking          - farmer enters 5 candidate crops -> AI ranks Top 3
  3. Profit Analysis       - pick one of the Top 3 (or type your own crop) ->
                              full profitability report

Step 2 -> Step 3 hand-off: clicking "Analyze profitability" under a Top-3
card stores the crop name in st.session_state under the SAME key the
Profit Analysis text_input uses, switches the active page, and reruns.
Streamlit then renders the Profit Analysis page with that crop pre-filled.

Run with:
    streamlit run app.py
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

# ------------------------------------------------------------------ #
# Path / env setup — MUST happen before importing backend.market_rag.*,
# since diagnose_crops.py builds its Groq client at import time and
# needs GROQ_API_KEY already in os.environ.
# ------------------------------------------------------------------ #
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))
load_dotenv(ROOT_DIR / ".env")

from backend.profit_analysis.pipeline import generate_full_report  # noqa: E402
from backend.market_analysis.retriever import retrieve, _get_collection  # noqa: E402
from backend.market_analysis.diagnose_crops import (  # noqa: E402
    SYSTEM_PROMPT,
    CHAT_MODEL,
    build_context_block,
    complete_chat,
    RateLimitError,
)
from backend.market_analysis.rank_crops import rank_crops  # noqa: E402


# ==================================================================== #
# PAGE CONFIG + STYLE
# ==================================================================== #

st.set_page_config(
    page_title="AgriMent",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main { background-color:#f8faf7; }
    h1 { color:#1b5e20 !important; font-size:42px !important; font-weight:800; }
    h2 { color:#2e7d32 !important; }
    h3 { color:#388e3c !important; }
    .card {
        background:white; padding:25px; border-radius:20px;
        border:1px solid #e0e0e0; box-shadow:0px 5px 20px rgba(0,0,0,0.06);
    }
    [data-testid="metric-container"] {
        background:white; padding:15px; border-radius:18px; border:1px solid #dcedc8;
    }
    .stButton button {
        background:linear-gradient(90deg,#2e7d32,#66bb6a);
        color:white; border:none; border-radius:12px; height:45px; font-weight:700;
    }
    .stButton button:hover { background:#1b5e20; }
    .stTextInput input { border-radius:12px; }
    section[data-testid="stSidebar"] {
        background:linear-gradient(180deg,#e8f5e9,#ffffff);
    }
    .streamlit-expanderHeader { background:#f1f8e9; border-radius:12px; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==================================================================== #
# SESSION STATE
# ==================================================================== #

if "history" not in st.session_state:
    st.session_state.history = []

if "crop_history" not in st.session_state:
    st.session_state.crop_history = []

if "active_page" not in st.session_state:
    st.session_state.active_page = "🌱 Crop Ranking"

# NOTE: this is the exact key the Profit Analysis crop text_input uses.
# Setting it here (before that widget is created) is what makes the
# pre-fill work.
if "profit_crop_input" not in st.session_state:
    st.session_state.profit_crop_input = ""


PAGES = ["📊 Market Intelligence", "🌱 Crop Ranking", "💰 Profit Analysis"]


def go_to_profit_analysis(crop_name: str) -> None:
    """Hand-off from a Top-3 card to the Profit Analysis page."""
    st.session_state.profit_crop_input = crop_name
    st.session_state.active_page = "💰 Profit Analysis"
    st.rerun()


# ==================================================================== #
# SIDEBAR
# ==================================================================== #

with st.sidebar:
    st.markdown(
        """
        <div class="card">
        <h2>🌱 AgriVision AI</h2>
        <p>Smart Agricultural Market Intelligence Platform</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    st.header("⚙️ Configuration")
    top_k = st.slider("Retrieved chunks", min_value=1, max_value=15, value=5)
    show_raw_chunks = st.checkbox("Show full chunk text", value=True)

    st.divider()
    st.subheader("📚 Knowledge Base")
    try:
        collection = _get_collection()
        st.success(f"{collection.name}\n\n{collection.count()} vectors")
    except RuntimeError as e:
        st.error(str(e))
        st.stop()

    st.divider()
    st.caption(f"🤖 Model: {CHAT_MODEL}")
    st.divider()

    if st.session_state.history:
        st.subheader("📊 Q&A History")
        st.caption(f"{len(st.session_state.history)} runs")
        export = json.dumps(st.session_state.history, ensure_ascii=False, indent=2)
        st.download_button(
            "Download Q&A JSON", data=export,
            file_name=f"qa_logs_{datetime.now():%Y%m%d_%H%M%S}.json",
            mime="application/json",
        )
        if st.button("Clear Q&A logs"):
            st.session_state.history = []
            st.rerun()

    if st.session_state.crop_history:
        st.subheader("🌱 Ranking History")
        st.caption(f"{len(st.session_state.crop_history)} runs")
        export = json.dumps(st.session_state.crop_history, ensure_ascii=False, indent=2)
        st.download_button(
            "Download Ranking JSON", data=export,
            file_name=f"ranking_logs_{datetime.now():%Y%m%d_%H%M%S}.json",
            mime="application/json",
        )
        if st.button("Clear Ranking logs"):
            st.session_state.crop_history = []
            st.rerun()


# ==================================================================== #
# HEADER
# ==================================================================== #

st.markdown(
    """
    <div class="card">
    <h1>🌱 AgriVision AI</h1>
    <h3>Agricultural Market Intelligence &amp; Profitability Assistant</h3>
    <p>AI-powered decision support: rank candidate crops by market opportunity,
    then run a full profitability analysis on the one you pick.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")

try:
    vector_count = _get_collection().count()
except Exception:
    vector_count = 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("📚 Knowledge Base", vector_count)
c2.metric("🤖 AI Model", CHAT_MODEL)
c3.metric("🌱 AI Modules", "RAG + Ranking + Profit")
c4.metric("🇫🇷 Market", "France")

st.divider()


# ==================================================================== #
# PAGE NAV  (radio, not st.tabs, so we can switch it programmatically)
# ==================================================================== #

active_page = st.radio(
    "Navigation",
    PAGES,
    key="active_page",
    horizontal=True,
    label_visibility="collapsed",
)

st.divider()


# ==================================================================== #
# PAGE 1: MARKET INTELLIGENCE (Q&A)
# ==================================================================== #

if active_page == "📊 Market Intelligence":

    st.markdown(
        """
        <div class="card">
        <h3>📊 Agricultural Market Assistant</h3>
        <p>Ask questions about crops, prices, trends and market opportunities.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    query = st.text_input("Question", placeholder="Example: Is tomato profitable in France?")
    run_clicked = st.button("🚀 Analyze", type="primary", disabled=not query.strip(), key="qa_run")

    if run_clicked:
        t0 = time.perf_counter()
        try:
            hits = retrieve(query, top_k=top_k)
        except Exception as e:
            st.error(f"Retrieval failed: {e}")
            st.stop()
        retrieval_time = time.perf_counter() - t0

        if not hits:
            st.warning("No information found in knowledge base.")
            st.session_state.history.append({
                "timestamp": datetime.now().isoformat(),
                "query": query, "num_hits": 0, "answer": None,
            })
            st.stop()

        avg_distance = sum(h["distance"] for h in hits) / len(hits)

        context_block = build_context_block(hits)
        user_message = f"Context:\n{context_block}\n\nQuestion: {query}"

        t1 = time.perf_counter()
        try:
            response = complete_chat(
                model=CHAT_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.2,
            )
            answer = response.choices[0].message.content
        except RateLimitError as e:
            st.warning(str(e))
            st.stop()
        except Exception as e:
            st.error(f"Generation failed: {e}")
            st.stop()
        generation_time = time.perf_counter() - t1

        a, b, c, d = st.columns(4)
        a.metric("⏱ Retrieval", f"{retrieval_time:.2f}s")
        b.metric("🤖 Generation", f"{generation_time:.2f}s")
        c.metric("📚 Chunks", len(hits))
        d.metric("🎯 Distance", f"{avg_distance:.3f}")

        st.divider()
        st.markdown(
            f"""<div class="card"><h3>🤖 AI Recommendation</h3><p>{answer}</p></div>""",
            unsafe_allow_html=True,
        )
        st.write("")

        col1, col2 = st.columns([1, 3])
        with col1:
            rating = st.radio(
                "Rating", ["Not rated", "Good", "Bad"], horizontal=True,
                key=f"rate_{len(st.session_state.history)}",
            )
        with col2:
            note = st.text_input("Note", key=f"note_{len(st.session_state.history)}")

        st.divider()
        st.subheader("📚 Retrieved Sources")
        for i, hit in enumerate(hits, start=1):
            meta = hit["metadata"]
            source = meta.get("source", "unknown")
            with st.expander(f"{i}. {source} - distance {hit['distance']:.4f}"):
                st.write(hit["text"] if show_raw_chunks else hit["text"][:300])

        st.session_state.history.append({
            "timestamp": datetime.now().isoformat(),
            "query": query, "num_hits": len(hits), "avg_distance": avg_distance,
            "retrieval_time": retrieval_time, "generation_time": generation_time,
            "answer": answer, "rating": rating, "note": note,
        })

    if st.session_state.history:
        st.divider()
        st.subheader("📜 Session History")
        st.dataframe(
            [
                {
                    "time": h["timestamp"][11:19],
                    "question": h["query"],
                    "chunks": h["num_hits"],
                    "rating": h.get("rating", ""),
                }
                for h in st.session_state.history
            ],
            use_container_width=True,
        )


# ==================================================================== #
# PAGE 2: CROP RANKING
# ==================================================================== #

elif active_page == "🌱 Crop Ranking":

    st.markdown(
        """
        <div class="card">
        <h3>🌱 Crop Market Ranking</h3>
        <p>Evaluate candidate crops and identify the most promising opportunities
        for the French agricultural market.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    st.subheader("🌾 Candidate Crops")

    crop_cols = st.columns(5)
    default_crops = ["tomate", "pomme de terre", "orge", "mais", "melon"]
    crop_inputs = []
    for i, col in enumerate(crop_cols):
        with col:
            crop_inputs.append(
                st.text_input(f"Culture {i+1}", value=default_crops[i], key=f"crop_input_{i}")
            )

    st.write("")
    rank_clicked = st.button("🚀 Analyze Crops", type="primary", key="rank_run")

    if rank_clicked:
        crops = [c.strip() for c in crop_inputs if c.strip()]
        if len(crops) < 2:
            st.warning("Enter at least 2 crops.")
            st.stop()

        t0 = time.perf_counter()
        try:
            with st.spinner("AI analysis running..."):
                result = rank_crops(crops, top_n=3)
        except RateLimitError as e:
            st.warning(str(e))
            st.stop()
        except Exception as e:
            st.error(f"Ranking failed: {e}")
            st.stop()
        total_time = time.perf_counter() - t0

        st.metric("⏱ Analysis Time", f"{total_time:.2f}s")
        st.divider()
        st.markdown("<h2>🏆 Top 3 Opportunities</h2>", unsafe_allow_html=True)

        top_cols = st.columns(3)
        for i, crop_result in enumerate(result["top"]):
            with top_cols[i]:
                culture = crop_result.get("culture", "Unknown")
                score = crop_result.get("score", "?")


                st.markdown(
                    f"""
                    <div class="card">
                    <h3>#{i+1} 🌱 {culture}</h3>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                
                st.write("")
                st.caption("Price trend: " + str(crop_result.get("tendance_prix", "Unknown")))
                st.write(crop_result.get("justification", ""))

                # --- Hand-off to Profit Analysis --------------------------
                st.button(
                    "💰 Analyze profitability",
                    key=f"to_profit_{i}",
                    on_click=go_to_profit_analysis,
                    args=(culture,),
                    use_container_width=True,
                )

                with st.expander("📊 Detailed statistics"):
                    stats = crop_result.get("stats", {})
                    st.write("Chunks found:", stats.get("chunks_trouves", "?"))
                    st.write("Sources:", ", ".join(stats.get("sources", [])))
                    st.write("Average rerank score:", stats.get("avg_rerank_score", "N/A"))
                    csv_trend = stats.get("tendance_csv")
                    if csv_trend:
                        st.write("CSV variation:", csv_trend.get("pct_change", "N/A"), "%")
                    st.write("Retrieval time:", stats.get("retrieval_time_s", "?"), "s")
                    st.write("Generation time:", stats.get("generation_time_s", "?"), "s")

        st.divider()
        st.subheader("📈 Market Opportunity Comparison")
        chart_data = {r.get("culture", "?"): r.get("score", 0) for r in result["all_evaluated"]}
        st.bar_chart(chart_data)

        st.divider()
        st.subheader("🌾 All Evaluated Crops")
        st.dataframe(
            [
                {
                    "Culture": r.get("culture"),
                    "Score": r.get("score"),
                    "Price Trend": r.get("tendance_prix"),
                    "Enough Data": r.get("donnees_suffisantes"),
                    "Justification": r.get("justification"),
                }
                for r in result["all_evaluated"]
            ],
            use_container_width=True,
        )

        st.session_state.crop_history.append({
            "timestamp": datetime.now().isoformat(),
            "crops": crops, "total_time": total_time,
            "top": result["top"], "all": result["all_evaluated"],
        })

    if st.session_state.crop_history:
        st.divider()
        st.subheader("📜 Ranking History")
        st.dataframe(
            [
                {
                    "time": h["timestamp"][11:19],
                    "crops": ", ".join(h["crops"]),
                    "winner": h["top"][0]["culture"] if h["top"] else None,
                    "time(s)": round(h["total_time"], 2),
                }
                for h in st.session_state.crop_history
            ],
            use_container_width=True,
        )


# ==================================================================== #
# PAGE 3: PROFIT ANALYSIS
# ==================================================================== #

elif active_page == "💰 Profit Analysis":

    st.markdown(
        """
        <div class="card">
        <h3>💰 Analyse de Rentabilité Agricole</h3>
        <p>RAG + IA prédictive + calculs économiques — estimation de rentabilité
        pour votre exploitation.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    import os as _os
    if not _os.environ.get("GROQ_API_KEY"):
        st.warning(
            "GROQ_API_KEY n'est pas défini. Ajoutez-le à un fichier .env à la racine "
            "du projet avant de lancer une analyse."
        )

    if st.session_state.profit_crop_input:
        st.info(f"Culture pré-remplie depuis le classement de marché : "
                f"**{st.session_state.profit_crop_input}**. Modifiez-la si besoin.")

    with st.form("farmer_input_form"):
        col1, col2 = st.columns(2)

        with col1:
            crop = st.text_input(
                "Culture", placeholder="ex: Blé tendre, Almonds, Maïs",
                key="profit_crop_input",
            )
            area_ha = st.number_input("Superficie (ha)", min_value=0.1, value=10.0, step=0.5)
            location = st.text_input("Localisation", value="France")

        with col2:
            irrigation = st.selectbox("Irrigation", ["Irrigué", "Non irrigué"])
            production_method = st.selectbox("Méthode de production", ["Conventionnelle", "Biologique"])
            budget = st.number_input(
                "Budget disponible (€) — optionnel",
                min_value=0.0, value=0.0, step=100.0,
                help="Laissez à 0 pour ignorer la vérification budgétaire.",
            )

        submitted = st.form_submit_button("Lancer l'analyse", type="primary", use_container_width=True)

    if submitted:
        if not crop.strip():
            st.error("Merci de renseigner une culture.")
            st.stop()

        farmer_input = {
            "crop": crop.strip(),
            "area_ha": area_ha,
            "location": location.strip() or "France",
            "irrigation": irrigation,
            "production_method": production_method,
            "budget": budget if budget > 0 else None,
        }

        with st.spinner("Récupération des données, extraction des prix/coûts et calcul en cours..."):
            try:
                result = generate_full_report(farmer_input)
            except Exception as e:
                st.error(f"Une erreur est survenue pendant l'analyse : {e}")
                st.stop()

        ind = result["indicators"]

        for w in result["warnings"]:
            st.warning(w)

        st.divider()
        st.subheader("📊 Indicateurs financiers")

        row1 = st.columns(4)
        row1[0].metric("Revenu brut", f"{ind['gross_revenue_eur']:,.0f} €")
        row1[1].metric("Coût total estimé", f"{ind['estimated_total_cost_eur']:,.0f} €")
        row1[2].metric("Profit estimé", f"{ind['estimated_profit_eur']:,.0f} €")
        row1[3].metric("Marge (%)", f"{ind['profit_margin_pct']:.1f}%")

        row2 = st.columns(4)
        row2[0].metric("ROI (%)", f"{ind['roi_pct']:.1f}%")
        row2[1].metric("Prix seuil de rentabilité", f"{ind['breakeven_selling_price_eur_per_ton']:,.0f} €/t")
        row2[2].metric("Rendement seuil", f"{ind['breakeven_yield_t_per_ha']:.2f} t/ha")
        row2[3].metric(
            "Budget suffisant ?", ind["budget_sufficiency"],
            delta=f"-{ind['budget_gap_eur']:,.0f} €" if ind["budget_sufficiency"] == "No" else None,
            delta_color="inverse",
        )

        row3 = st.columns(2)
        risk_color = {"Low": "🟢", "Medium": "🟠", "High": "🔴"}.get(ind["risk_score"], "")
        conf_color = {"Low": "🔴", "Medium": "🟠", "High": "🟢"}.get(ind["confidence_score"], "")
        with row3[0]:
            st.markdown(f"**Niveau de risque : {risk_color} {ind['risk_score']}**")
            for reason in ind["risk_reasons"]:
                st.caption(f"• {reason}")
        with row3[1]:
            st.markdown(f"**Confiance dans les données : {conf_color} {ind['confidence_score']}**")
            for reason in ind["confidence_reasons"]:
                st.caption(f"• {reason}")

        st.divider()
        st.subheader("📝 Rapport détaillé")
        st.markdown(result["narrative"])

        if result["sources_used"]:
            with st.expander("📎 Sources utilisées"):
                for s in result["sources_used"]:
                    st.write(f"- {s}")

        extraction = result.get("extraction_detail", {})
        if extraction.get("price_evidence") or extraction.get("cost_evidence"):
            with st.expander("🔍 Détail de l'extraction (prix/coût)"):
                st.write(f"Confiance d'extraction : {extraction.get('extraction_confidence')}")
                if extraction.get("price_evidence"):
                    st.write(f"Prix : {extraction['price_evidence']}")
                if extraction.get("cost_evidence"):
                    st.write(f"Coût : {extraction['cost_evidence']}")


# ==================================================================== #
# FOOTER
# ==================================================================== #

st.divider()
st.markdown(
    """
    <center>
    🌱 <b>AgriMent AI</b><br>
    Market Ranking + Profitability Analysis, powered by RAG + Groq
    </center>
    """,
    unsafe_allow_html=True,
)