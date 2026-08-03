"""
Rebuild the local vector store from FranceAgriMer PDFs + Agreste CSVs
found in the shared `data/` folder (or MARKET_DATA_DIR).

Uses Mistral embeddings (same family as agent_agriculture) — no local
sentence-transformers download required.

Run from backend/agent_business:
    python -m app.market_intelligence.rag.ingest
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm

# Load repo-root .env before embedding client reads MISTRAL_API_KEY
load_dotenv(Path(__file__).resolve().parents[5] / ".env")
load_dotenv()

from app.market_intelligence.ipap_parser import parse_ippap_csv
from app.market_intelligence.paths import (
    list_ippap_csvs,
    list_market_pdfs,
    resolve_market_data_dir,
)
from app.market_intelligence.rag.embeddings import embed_texts
from app.market_intelligence.rag.local_store import LocalVectorStore

STORE_DIR = Path(__file__).resolve().parent / "vector_store"
COLLECTION_NAME = "agri_market_data"
CSV_CHUNK_SIZE = 800
CSV_CHUNK_OVERLAP = 150
EMBED_BATCH_SIZE = 32
CSV_INGEST_MIN_YEAR = 2023
PDF_CHAR_CHUNK = 1200
PDF_CHAR_OVERLAP = 200


def chunk_text(text: str, chunk_size: int = CSV_CHUNK_SIZE, overlap: int = CSV_CHUNK_OVERLAP):
    text = " ".join(text.split())
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += max(1, chunk_size - overlap)
    return chunks


def _load_pdfs_pypdf(pdf_paths: list[Path]) -> list[dict]:
    try:
        from pypdf import PdfReader
    except ImportError:
        print("[warn] pypdf not installed — cannot parse PDFs.")
        return []

    documents: list[dict] = []
    for pdf_path in pdf_paths:
        print(f"  [pypdf] {pdf_path.name}...")
        try:
            reader = PdfReader(str(pdf_path))
        except Exception as e:
            print(f"[warn] Could not open {pdf_path.name}: {e}")
            continue
        page_count = 0
        for page_idx, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            pieces = chunk_text(text, PDF_CHAR_CHUNK, PDF_CHAR_OVERLAP)
            page_count += len(pieces)
            for piece in pieces:
                documents.append(
                    {
                        "text": piece,
                        "source": pdf_path.name,
                        "page": page_idx,
                        "doc_type": "pdf",
                    }
                )
        print(f"    -> {page_count} chunks from {len(reader.pages)} pages")
    return documents


def load_pdfs(pdf_paths: list[Path]) -> list[dict]:
    if not pdf_paths:
        print("[warn] No PDF files found in market data directory.")
        return []
    print("[info] Parsing PDFs with pypdf...")
    return _load_pdfs_pypdf(pdf_paths)


def load_csv_docs(csv_paths: list[Path]) -> list[dict]:
    """Compact recent IPPAP rows for RAG (full history stays in pandas)."""
    documents: list[dict] = []
    for csv_path in csv_paths:
        try:
            df = parse_ippap_csv(csv_path)
        except Exception as e:
            print(f"[warn] Could not parse {csv_path.name}: {e}")
            continue
        if "annee" in df.columns:
            df = df[df["annee"] >= CSV_INGEST_MIN_YEAR]
        # Cap volume: keep most-specific products only (niveau >= 3)
        if "niveau_hierarchie" in df.columns:
            df = df[df["niveau_hierarchie"] >= 3]
        for idx, row in df.iterrows():
            text = (
                f"Produit: {row['produit_nom']}, "
                f"Annee: {row['annee']}, Mois: {row['mois_num']}, "
                f"Indice (base 100 en 2020): {row['valeur']}, "
                f"Qualite: {row['qualite']}"
            )
            documents.append(
                {
                    "text": text,
                    "source": csv_path.name,
                    "row": int(idx),
                    "doc_type": "csv",
                }
            )
    return documents


def main():
    data_dir = resolve_market_data_dir()
    print(f"Market data dir: {data_dir}")
    if data_dir is None:
        print("No data directory found. Put FDS_IPPAP_*.csv and FranceAgriMer_*.pdf in ./data")
        return

    pdf_paths = list_market_pdfs(data_dir)
    csv_paths = list_ippap_csvs(data_dir)
    print(f"PDFs ({len(pdf_paths)}): {[p.name for p in pdf_paths]}")
    print(f"CSVs ({len(csv_paths)}): {[p.name for p in csv_paths]}")

    store = LocalVectorStore(STORE_DIR, COLLECTION_NAME)
    store.reset()

    print("Loading PDFs...")
    pdf_chunks_raw = load_pdfs(pdf_paths)
    print(f"Produced {len(pdf_chunks_raw)} PDF chunks.")

    # CSVs are already used structurally via pandas (price_trends). Optional RAG
    # ingest of recent rows — off by default to keep Mistral embed quota sane.
    include_csv = os.environ.get("INCLUDE_CSV_IN_RAG", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    csv_docs: list[dict] = []
    if include_csv:
        print(f"Loading CSV rows (year >= {CSV_INGEST_MIN_YEAR}, hierarchy >= 3)...")
        csv_docs = load_csv_docs(csv_paths)
        print(f"Loaded {len(csv_docs)} CSV rows for RAG.")
    else:
        print("[info] Skipping CSV→RAG (trends use pandas). Set INCLUDE_CSV_IN_RAG=1 to enable.")

    chunks: list[str] = []
    metadatas: list[dict] = []

    for doc in pdf_chunks_raw:
        chunks.append(doc["text"])
        meta = {"source": doc["source"], "doc_type": "pdf"}
        if doc.get("page") is not None:
            meta["page"] = int(doc["page"])
        metadatas.append(meta)

    for doc in csv_docs:
        for piece in chunk_text(doc["text"]):
            chunks.append(piece)
            metadatas.append(
                {"source": doc["source"], "row": int(doc["row"]), "doc_type": "csv"}
            )

    print(f"Total chunks to embed via Mistral: {len(chunks)}")
    if not chunks:
        print("No chunks to ingest.")
        return

    for i in tqdm(range(0, len(chunks), EMBED_BATCH_SIZE)):
        batch_texts = chunks[i : i + EMBED_BATCH_SIZE]
        batch_meta = metadatas[i : i + EMBED_BATCH_SIZE]
        embeddings = embed_texts(batch_texts)
        store.add(embeddings=embeddings, documents=batch_texts, metadatas=batch_meta)

    n_pdf = sum(1 for m in metadatas if m.get("doc_type") == "pdf")
    n_csv = len(metadatas) - n_pdf
    print(
        f"Done. Store '{COLLECTION_NAME}' has {store.count()} vectors "
        f"({n_pdf} PDF chunks, {n_csv} CSV chunks) → {STORE_DIR}"
    )


if __name__ == "__main__":
    main()
