"""
app.py
AgriVision AI - Agricultural Market Analysis Assistant

Run:
    streamlit run app.py
"""

import time
import json
from datetime import datetime

import streamlit as st


from rag.retriever import retrieve, _get_collection
from rag.diagnose_crops import (
    SYSTEM_PROMPT,
    CHAT_MODEL,
    build_context_block,
    complete_chat,
    RateLimitError,
)
from rag.rank_crops import rank_crops



# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AgriVision AI",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)



# ============================================================
# CUSTOM DESIGN
# ============================================================

st.markdown(
"""
<style>


/* Main background */

.main {
    background-color:#f8faf7;
}



/* Titles */

h1 {

    color:#1b5e20 !important;
    font-size:42px !important;
    font-weight:800;

}


h2 {

    color:#2e7d32 !important;

}


h3 {

    color:#388e3c !important;

}



/* Cards */

.card {

    background:white;

    padding:25px;

    border-radius:20px;

    border:1px solid #e0e0e0;

    box-shadow:
    0px 5px 20px rgba(0,0,0,0.06);

}



/* Metrics */

[data-testid="metric-container"] {

    background:white;

    padding:15px;

    border-radius:18px;

    border:1px solid #dcedc8;

}



/* Buttons */

.stButton button {

    background:
    linear-gradient(
        90deg,
        #2e7d32,
        #66bb6a
    );

    color:white;

    border:none;

    border-radius:12px;

    height:45px;

    font-weight:700;

}


.stButton button:hover {

    background:#1b5e20;

}



/* Text inputs */

.stTextInput input {

    border-radius:12px;

}



/* Sidebar */

section[data-testid="stSidebar"] {

    background:
    linear-gradient(
        180deg,
        #e8f5e9,
        #ffffff
    );

}



/* Tabs */

button[data-baseweb="tab"] {

    font-size:18px;

    font-weight:600;

}



/* Expanders */

.streamlit-expanderHeader {

    background:#f1f8e9;

    border-radius:12px;

}


</style>

""",
unsafe_allow_html=True
)





# ============================================================
# SESSION STATE
# ============================================================

if "history" not in st.session_state:

    st.session_state.history = []


if "crop_history" not in st.session_state:

    st.session_state.crop_history = []





# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:


    st.markdown(
    """

    <div class="card">

    <h2>
    🌱 AgriVision AI
    </h2>


    <p>
    Smart Agricultural Market Intelligence Platform
    </p>


    </div>

    """,

    unsafe_allow_html=True
    )


    st.write("")


    st.header("⚙️ Configuration")


    top_k = st.slider(
        "Retrieved chunks",
        min_value=1,
        max_value=15,
        value=5
    )


    show_raw_chunks = st.checkbox(
        "Show full chunk text",
        value=True
    )



    st.divider()



    st.subheader("📚 Knowledge Base")


    try:

        collection = _get_collection()

        st.success(
            f"{collection.name}\n\n{collection.count()} vectors"
        )


    except RuntimeError as e:

        st.error(str(e))

        st.stop()



    st.divider()



    st.caption(
        f"🤖 Model: {CHAT_MODEL}"
    )



    st.divider()



    # -------------------------
    # Q&A Logs
    # -------------------------

    if st.session_state.history:


        st.subheader(
            "📊 Q&A History"
        )


        st.caption(
            f"{len(st.session_state.history)} runs"
        )


        export = json.dumps(
            st.session_state.history,
            ensure_ascii=False,
            indent=2
        )


        st.download_button(
            "Download Q&A JSON",
            data=export,
            file_name=
            f"qa_logs_{datetime.now():%Y%m%d_%H%M%S}.json",
            mime="application/json"
        )


        if st.button(
            "Clear Q&A logs"
        ):

            st.session_state.history=[]

            st.rerun()



    # -------------------------
    # Ranking Logs
    # -------------------------

    if st.session_state.crop_history:


        st.subheader(
            "🌱 Ranking History"
        )


        st.caption(
            f"{len(st.session_state.crop_history)} runs"
        )


        export = json.dumps(
            st.session_state.crop_history,
            ensure_ascii=False,
            indent=2
        )


        st.download_button(
            "Download Ranking JSON",
            data=export,
            file_name=
            f"ranking_logs_{datetime.now():%Y%m%d_%H%M%S}.json",
            mime="application/json"
        )


        if st.button(
            "Clear Ranking logs"
        ):

            st.session_state.crop_history=[]

            st.rerun()
# ============================================================
# HEADER
# ============================================================


st.markdown(
"""
<div class="card">

<h1>
🌱 AgriVision AI
</h1>


<h3>
Agricultural Market Intelligence Assistant
</h3>


<p>
AI-powered decision support system using
RAG + Mistral AI to analyze agricultural markets,
prices and opportunities.
</p>


</div>

""",
unsafe_allow_html=True
)



st.write("")



# ============================================================
# DASHBOARD METRICS
# ============================================================


try:

    vector_count = _get_collection().count()

except:

    vector_count = 0



c1,c2,c3,c4 = st.columns(4)



with c1:

    st.metric(
        "📚 Knowledge Base",
        vector_count
    )



with c2:

    st.metric(
        "🤖 AI Model",
        CHAT_MODEL
    )



with c3:

    st.metric(
        "🌱 AI Modules",
        "RAG + Ranking"
    )



with c4:

    st.metric(
        "🇫🇷 Market",
        "France"
    )



st.divider()



# ============================================================
# TABS
# ============================================================


tab_qa, tab_ranking = st.tabs(
[
    "📊 Market Intelligence",
    "🌱 Crop Ranking"
]
)





# ============================================================
# TAB 1 : QUESTION ANSWERING
# ============================================================


with tab_qa:


    st.markdown(
    """
    <div class="card">

    <h3>
    📊 Agricultural Market Assistant
    </h3>

    <p>
    Ask questions about crops, prices,
    trends and market opportunities.
    </p>

    </div>
    """,

    unsafe_allow_html=True
    )


    st.write("")



    query = st.text_input(
        "Question",
        placeholder=
        "Example: Is tomato profitable in France?"
    )


    run_clicked = st.button(
        "🚀 Analyze",
        type="primary",
        disabled=not query.strip(),
        key="qa_run"
    )



    if run_clicked:


        # -------------------------
        # Retrieval
        # -------------------------

        t0=time.perf_counter()


        try:

            hits = retrieve(
                query,
                top_k=top_k
            )


        except Exception as e:

            st.error(
                f"Retrieval failed: {e}"
            )

            st.stop()



        retrieval_time = (
            time.perf_counter()-t0
        )



        if not hits:


            st.warning(
                "No information found in knowledge base."
            )


            st.session_state.history.append(
            {

                "timestamp":
                datetime.now().isoformat(),

                "query":
                query,

                "num_hits":
                0,

                "answer":
                None

            })


            st.stop()



        avg_distance = sum(
            h["distance"]
            for h in hits
        ) / len(hits)



        # -------------------------
        # Generation
        # -------------------------


        context_block = build_context_block(
            hits
        )


        user_message = (
            f"Context:\n{context_block}"
            f"\n\nQuestion: {query}"
        )



        t1=time.perf_counter()



        try:


            response = complete_chat(

                model=CHAT_MODEL,

                messages=[

                    {
                    "role":"system",
                    "content":SYSTEM_PROMPT
                    },


                    {
                    "role":"user",
                    "content":user_message
                    }

                ],

                temperature=0.2

            )



            answer = (
                response
                .choices[0]
                .message
                .content
            )



        except RateLimitError as e:


            st.warning(str(e))

            st.stop()


        except Exception as e:


            st.error(
                f"Generation failed: {e}"
            )

            st.stop()



        generation_time = (
            time.perf_counter()-t1
        )



        # -------------------------
        # Performance cards
        # -------------------------


        a,b,c,d = st.columns(4)



        a.metric(
            "⏱ Retrieval",
            f"{retrieval_time:.2f}s"
        )


        b.metric(
            "🤖 Generation",
            f"{generation_time:.2f}s"
        )


        c.metric(
            "📚 Chunks",
            len(hits)
        )


        d.metric(
            "🎯 Distance",
            f"{avg_distance:.3f}"
        )



        st.divider()



        # -------------------------
        # AI Answer
        # -------------------------


        st.markdown(
        f"""

        <div class="card">


        <h3>
        🤖 AI Recommendation
        </h3>


        <p>
        {answer}
        </p>


        </div>


        """,

        unsafe_allow_html=True
        )



        st.write("")



        # -------------------------
        # Rating
        # -------------------------


        col1,col2 = st.columns(
            [1,3]
        )



        with col1:

            rating = st.radio(
                "Rating",
                [
                    "Not rated",
                    "Good",
                    "Bad"
                ],

                horizontal=True,

                key=
                f"rate_{len(st.session_state.history)}"
            )



        with col2:

            note = st.text_input(
                "Note",
                key=
                f"note_{len(st.session_state.history)}"
            )



        st.divider()



        # -------------------------
        # Sources
        # -------------------------


        st.subheader(
            "📚 Retrieved Sources"
        )



        for i,hit in enumerate(
            hits,
            start=1
        ):


            meta = hit["metadata"]


            source = meta.get(
                "source",
                "unknown"
            )


            with st.expander(
                f"{i}. {source} "
                f"- distance {hit['distance']:.4f}"
            ):


                if show_raw_chunks:

                    st.write(
                        hit["text"]
                    )


                else:

                    st.write(
                        hit["text"][:300]
                    )



        # -------------------------
        # Save history
        # -------------------------


        st.session_state.history.append(

        {


        "timestamp":
        datetime.now().isoformat(),


        "query":
        query,


        "num_hits":
        len(hits),


        "avg_distance":
        avg_distance,


        "retrieval_time":
        retrieval_time,


        "generation_time":
        generation_time,


        "answer":
        answer,


        "rating":
        rating,


        "note":
        note


        }

        )



    # History table


    if st.session_state.history:


        st.divider()


        st.subheader(
            "📜 Session History"
        )


        st.dataframe(

        [

        {

        "time":
        h["timestamp"][11:19],

        "question":
        h["query"],

        "chunks":
        h["num_hits"],

        "rating":
        h.get(
            "rating",
            ""
        )

        }

        for h in st.session_state.history

        ],

        use_container_width=True

        )
# ============================================================
# TAB 2 : CROP RANKING
# ============================================================


with tab_ranking:


    st.markdown(
    """

    <div class="card">


    <h3>
    🌱 Crop Market Ranking
    </h3>


    <p>
    Evaluate candidate crops and identify
    the most promising opportunities for
    the French agricultural market.
    </p>


    </div>


    """,

    unsafe_allow_html=True
    )


    st.write("")



    st.subheader(
        "🌾 Candidate Crops"
    )



    crop_cols = st.columns(5)



    default_crops = [

        "tomate",
        "pomme de terre",
        "avocat",
        "mangue",
        "banane"

    ]



    crop_inputs = []



    for i,col in enumerate(crop_cols):


        with col:


            crop_inputs.append(

                st.text_input(

                    f"Culture {i+1}",

                    value=
                    default_crops[i],

                    key=
                    f"crop_input_{i}"

                )

            )




    st.write("")



    rank_clicked = st.button(

        "🚀 Analyze Crops",

        type="primary",

        key="rank_run"

    )





    if rank_clicked:



        crops = [

            c.strip()

            for c in crop_inputs

            if c.strip()

        ]



        if len(crops)<2:


            st.warning(
                "Enter at least 2 crops."
            )

            st.stop()




        t0=time.perf_counter()



        try:


            with st.spinner(

                "AI analysis running..."

            ):


                result = rank_crops(

                    crops,

                    top_n=3

                )



        except RateLimitError as e:


            st.warning(str(e))

            st.stop()


        except Exception as e:


            st.error(

                f"Ranking failed: {e}"

            )


            st.stop()




        total_time = (
            time.perf_counter()-t0
        )




        st.metric(

            "⏱ Analysis Time",

            f"{total_time:.2f}s"

        )



        st.divider()



        # -------------------------
        # TOP 3 CARDS
        # -------------------------


        st.markdown(

        """

        <h2>
        🏆 Top 3 Opportunities
        </h2>

        """,

        unsafe_allow_html=True

        )



        top_cols = st.columns(3)




        for i,crop_result in enumerate(

            result["top"]

        ):



            with top_cols[i]:


                culture = crop_result.get(

                    "culture",

                    "Unknown"

                )



                score = crop_result.get(

                    "score",

                    "?"

                )




                st.markdown(

                f"""

                <div class="card">


                <h3>
                #{i+1} 🌱 {culture}
                </h3>


                <h2>
                {score}
                </h2>


                </div>

                """,

                unsafe_allow_html=True

                )



                st.write("")



                st.caption(

                    "Price trend: "

                    +

                    str(

                    crop_result.get(

                    "tendance_prix",

                    "Unknown"

                    )

                    )

                )



                st.write(

                    crop_result.get(

                    "justification",

                    ""

                    )

                )




                with st.expander(

                    "📊 Detailed statistics"

                ):



                    stats = crop_result.get(

                        "stats",

                        {}

                    )



                    st.write(

                        "Chunks found:",

                        stats.get(

                            "chunks_trouves",

                            "?"

                        )

                    )


                    st.write(

                        "Sources:",

                        ", ".join(

                            stats.get(

                                "sources",

                                []

                            )

                        )

                    )



                    st.write(

                        "Average rerank score:",

                        stats.get(

                            "avg_rerank_score",

                            "N/A"

                        )

                    )



                    csv_trend = stats.get(

                        "tendance_csv"

                    )



                    if csv_trend:


                        st.write(

                            "CSV variation:",

                            csv_trend.get(

                                "pct_change",

                                "N/A"

                            ),

                            "%"

                        )



                    st.write(

                        "Retrieval time:",

                        stats.get(

                            "retrieval_time_s",

                            "?"

                        ),

                        "s"

                    )



                    st.write(

                        "Generation time:",

                        stats.get(

                            "generation_time_s",

                            "?"

                        ),

                        "s"

                    )




        st.divider()



        # -------------------------
        # SCORE CHART
        # -------------------------


        st.subheader(

            "📈 Market Opportunity Comparison"

        )



        chart_data = {


            r.get(

                "culture",

                "?"

            ):

            r.get(

                "score",

                0

            )


            for r in result["all_evaluated"]

        }



        st.bar_chart(

            chart_data

        )




        st.divider()



        # -------------------------
        # TABLE
        # -------------------------


        st.subheader(

            "🌾 All Evaluated Crops"

        )



        st.dataframe(

        [

        {


        "Culture":

        r.get(

            "culture"

        ),



        "Score":

        r.get(

            "score"

        ),



        "Price Trend":

        r.get(

            "tendance_prix"

        ),



        "Enough Data":

        r.get(

            "donnees_suffisantes"

        ),



        "Justification":

        r.get(

            "justification"

        )


        }


        for r in result["all_evaluated"]

        ],


        use_container_width=True


        )





        # -------------------------
        # SAVE HISTORY
        # -------------------------


        st.session_state.crop_history.append(

        {


        "timestamp":

        datetime.now().isoformat(),



        "crops":

        crops,



        "total_time":

        total_time,



        "top":

        result["top"],



        "all":

        result["all_evaluated"]


        }

        )





    # Ranking history


    if st.session_state.crop_history:


        st.divider()



        st.subheader(

            "📜 Ranking History"

        )



        st.dataframe(

        [

        {


        "time":

        h["timestamp"][11:19],



        "crops":

        ", ".join(

            h["crops"]

        ),



        "winner":

        h["top"][0]["culture"]

        if h["top"]

        else None,



        "time(s)":

        round(

            h["total_time"],

            2

        )


        }




        for h in st.session_state.crop_history

        ],


        use_container_width=True

        )



# ============================================================
# FOOTER
# ============================================================


st.divider()


st.markdown(

"""

<center>

🌱 <b>AgriVision AI</b><br>

Powered by RAG + Mistral AI + Agricultural Data Intelligence

</center>

""",

unsafe_allow_html=True

)
