"""
retriever.py
Embeds a query locally (sentence-transformers) and searches Chroma.
No API key needed for retrieval itself.
"""

from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer, CrossEncoder

CHROMA_DIR = str(Path(__file__).resolve().parent / "chroma_db")
COLLECTION_NAME = "agri_market_data"
EMBED_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
RERANKER_MODEL_NAME = "antoinelouis/crossencoder-mMiniLMv2-L12-mmarcoFR"

# How many candidates to pull from the vector search before reranking.
# Must be >= top_k requested; wider net = reranker has more to choose from.
CANDIDATE_MULTIPLIER = 4

# Loading these models can take minutes on their first run.  Keep module import
# lightweight so Streamlit can render the interface immediately, then load them
# only when a user actually runs a market search.
embed_model: SentenceTransformer | None = None
reranker_model: CrossEncoder | None = None
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)


def _get_models() -> tuple[SentenceTransformer, CrossEncoder]:
    """Load and cache retrieval models on first use."""
    global embed_model, reranker_model

    if embed_model is None:
        # The model was downloaded during setup.  Avoid a Hugging Face network
        # check on every startup/search; this also lets the app work offline.
        embed_model = SentenceTransformer(EMBED_MODEL_NAME, local_files_only=True)
    if reranker_model is None:
        reranker_model = CrossEncoder(RERANKER_MODEL_NAME, local_files_only=True)
    return embed_model, reranker_model


def _get_collection():
    try:
        return chroma_client.get_collection(COLLECTION_NAME)
    except Exception as e:
        raise RuntimeError(
            f"Collection '{COLLECTION_NAME}' not found. Run ingest.py first."
        ) from e


def embed_query(query: str) -> list[float]:
    model, _ = _get_models()
    return model.encode([query])[0].tolist()


def retrieve(query: str, top_k: int = 5, where: dict | None = None):
    """
    Two-stage retrieval:
    1. Vector search pulls a wider pool of candidates (fast, approximate).
    2. Cross-encoder reranks those candidates against the query (slower,
       far more precise) and only the true top_k survive.

    Returns a list of dicts: {text, metadata, distance, rerank_score}
    ordered from most to least relevant (by rerank_score).
    """
    collection = _get_collection()
    query_embedding = embed_query(query)

    candidate_k = max(top_k * CANDIDATE_MULTIPLIER, top_k)
    query_args = {
        "query_embeddings": [query_embedding],
        "n_results": candidate_k,
    }
    if where:
        query_args["where"] = where
    results = collection.query(**query_args)

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    if not documents:
        return []

    # Stage 2: rerank candidates with the cross-encoder.
    pairs = [(query, doc) for doc in documents]
    _, reranker = _get_models()
    rerank_scores = reranker.predict(pairs)

    combined = list(zip(documents, metadatas, distances, rerank_scores))
    combined.sort(key=lambda x: x[3], reverse=True)  # higher rerank_score = more relevant
    combined = combined[:top_k]

    hits = []
    for text, meta, dist, score in combined:
        hits.append({
            "text": text,
            "metadata": meta,
            "distance": dist,
            "rerank_score": float(score),
        })
    return hits


if __name__ == "__main__":
    q = input("Query: ")
    for i, hit in enumerate(retrieve(q), start=1):
        print(f"\n--- Result {i} (distance={hit['distance']:.4f}) ---")
        print(f"Source: {hit['metadata']}")
        print(hit["text"][:300])
