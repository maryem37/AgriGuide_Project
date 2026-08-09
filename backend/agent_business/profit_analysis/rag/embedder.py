"""
embedder.py
------------
PDF ingestion + embedding pipeline for the profit-analysis RAG system.

Pipeline: PDF -> Docling (layout-aware parsing) -> HybridChunker (token-aware,
heading-preserving chunks) -> sentence-transformers embeddings -> ChromaDB
(persistent local vector store).

Only PDFs go through this path. CSVs are handled separately in
csv_retriever.py via pandas, since they're structured tabular data and
embedding numeric rows into a vector space is not useful for retrieval.

NOTE: docling pulls in torch and layout models — first run will download
model weights and may take a few minutes. Run `python embedder.py --ingest`
once locally to build the persistent index before starting the API server.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from typing import Iterable

import chromadb
from chromadb.utils import embedding_functions
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker


# Resolve paths from this source file so moving the repository never breaks
# report generation.  The persistent index already lives beside this module.
PROFIT_ANALYSIS_DIR = Path(__file__).resolve().parents[1]
PDF_DIR = PROFIT_ANALYSIS_DIR / "pdf"
CHROMA_DIR = Path(__file__).resolve().parent / "chroma_store"
COLLECTION_NAME = "farm_docs"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _stable_id(source: str, chunk_index: int, text: str) -> str:
    """Deterministic chunk id so re-ingesting the same PDF doesn't duplicate entries."""
    h = hashlib.sha256(f"{source}:{chunk_index}:{text[:80]}".encode("utf-8")).hexdigest()[:16]
    return f"{Path(source).stem}_{chunk_index}_{h}"


def get_collection():
    """Returns (creating if needed) the persistent Chroma collection."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    return client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=ef)


def ingest_pdf(path: Path, collection) -> int:
    """
    Converts one PDF with docling, chunks it with HybridChunker (which keeps
    section headings attached to their content — important for French
    agricultural PDFs with tables of per-crop production costs), and upserts
    into the vector store.

    Returns number of chunks ingested.
    """
    converter = DocumentConverter()
    result = converter.convert(str(path))
    doc = result.document

    chunker = HybridChunker(tokenizer=EMBEDDING_MODEL, max_tokens=384)
    chunks = list(chunker.chunk(doc))

    if not chunks:
        return 0

    ids, texts, metadatas = [], [], []
    for i, chunk in enumerate(chunks):
        # chunk.text is the contextualized text (includes heading context)
        text = chunker.contextualize(chunk) if hasattr(chunker, "contextualize") else chunk.text
        ids.append(_stable_id(path.name, i, text))
        texts.append(text)
        metadatas.append({
            "source": path.name,
            "chunk_index": i,
        })

    collection.upsert(ids=ids, documents=texts, metadatas=metadatas)
    return len(chunks)


def ingest_all_pdfs(pdf_dir: Path = PDF_DIR) -> dict:
    """Ingests every PDF in the given directory. Returns {filename: n_chunks}."""
    collection = get_collection()
    stats = {}
    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        try:
            n = ingest_pdf(pdf_path, collection)
            stats[pdf_path.name] = n
            print(f"  [ok] {pdf_path.name}: {n} chunks")
        except Exception as e:  # noqa: BLE001 - report and continue with other files
            stats[pdf_path.name] = f"ERROR: {e}"
            print(f"  [fail] {pdf_path.name}: {e}")
    return stats


def query_docs(query: str, n_results: int = 5, source_filter: str | None = None) -> list[dict]:
    """
    Semantic search over the ingested PDF chunks.
    Returns list of {text, source, distance} sorted by relevance.
    """
    collection = get_collection()
    where = {"source": source_filter} if source_filter else None
    res = collection.query(query_texts=[query], n_results=n_results, where=where)

    out = []
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    for text, meta, dist in zip(docs, metas, dists):
        out.append({"text": text, "source": meta.get("source"), "distance": dist})
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest / query the PDF vector store.")
    parser.add_argument("--ingest", action="store_true", help="Ingest all PDFs in data/pdf")
    parser.add_argument("--query", type=str, help="Run a test semantic query")
    args = parser.parse_args()

    if args.ingest:
        print(f"Ingesting PDFs from {PDF_DIR} ...")
        ingest_all_pdfs()

    if args.query:
        for r in query_docs(args.query):
            print(f"\n[{r['source']}] (distance={r['distance']:.3f})\n{r['text'][:300]}...")
