"""
ingest.py
Rebuilds the Chroma vector store from scratch.
- PDFs: parsed and chunked with Docling (structure- and table-aware).
- CSV: loaded row-by-row with pandas, same as before.
- Embeddings: local sentence-transformers model (no API key needed).
"""

import uuid
from pathlib import Path

import pandas as pd
import chromadb
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from ippap_parser import parse_ippap_csv

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent  # project root (parent of rag/)
MARKET_DIR = BASE_DIR / "market"
PDF_DIR = MARKET_DIR / "franceagrimer"
AGRESTE_DIR = MARKET_DIR / "agreste"


def _find_csv(agreste_dir: Path):
    """Returns all CSV files in the agreste folder (e.g. one per year),
    sorted by name so ingestion order is deterministic."""
    if not agreste_dir.exists():
        return []
    return sorted(agreste_dir.glob("*.csv"))

CHROMA_DIR = str(Path(__file__).resolve().parent / "chroma_db")
COLLECTION_NAME = "agri_market_data"

# Multilingual model: your source documents are in French.
EMBED_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

CSV_CHUNK_SIZE = 800     # character chunking, CSV rows only
CSV_CHUNK_OVERLAP = 150
EMBED_BATCH_SIZE = 64

# ---------------------------------------------------------------------------
# Clients / models
# ---------------------------------------------------------------------------
print(f"Loading embedding model '{EMBED_MODEL_NAME}' (first run downloads it, ~470MB)...")
embed_model = SentenceTransformer(EMBED_MODEL_NAME)
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

doc_converter = DocumentConverter()
# tokenizer= matches chunk sizes to our embedding model's token limits
chunker = HybridChunker(tokenizer=EMBED_MODEL_NAME)


# ---------------------------------------------------------------------------
# PDF loading via Docling
# ---------------------------------------------------------------------------
def load_pdfs_with_docling(pdf_dir: Path):
    """Returns list of dicts: {text, source, page}."""
    documents = []
    if not pdf_dir.exists():
        print(f"[warn] PDF dir not found: {pdf_dir}")
        return documents

    pdf_files = sorted(pdf_dir.glob("*.pdf"))
    for pdf_path in pdf_files:
        print(f"  Parsing {pdf_path.name} with Docling...")
        try:
            result = doc_converter.convert(str(pdf_path))
            dl_doc = result.document
        except Exception as e:
            print(f"[warn] Could not parse {pdf_path.name}: {e}")
            continue

        chunk_iter = chunker.chunk(dl_doc=dl_doc)
        for chunk in chunk_iter:
            # contextualize() adds heading/section context to the raw chunk text -
            # this is the text you want to embed, not chunk.text alone.
            enriched_text = chunker.contextualize(chunk)
            if not enriched_text.strip():
                continue

            page_no = None
            if chunk.meta.doc_items and chunk.meta.doc_items[0].prov:
                page_no = chunk.meta.doc_items[0].prov[0].page_no

            documents.append({
                "text": enriched_text,
                "source": pdf_path.name,
                "page": page_no,
                "doc_type": "pdf",
            })
    return documents


# ---------------------------------------------------------------------------
# CSV loading (unchanged approach)
# ---------------------------------------------------------------------------
def chunk_text(text: str, chunk_size: int = CSV_CHUNK_SIZE, overlap: int = CSV_CHUNK_OVERLAP):
    text = " ".join(text.split())
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def load_csv(csv_paths):
    documents = []
    if not csv_paths:
        print(f"[warn] No CSVs found in {AGRESTE_DIR}")
        return documents

    for csv_path in csv_paths:
        try:
            df = parse_ippap_csv(csv_path)
        except Exception as e:
            print(f"[warn] Could not parse {csv_path.name}: {e}")
            continue

        for idx, row in df.iterrows():
            text = (
                f"Produit: {row['produit_nom']}, "
                f"Annee: {row['annee']}, Mois: {row['mois_num']}, "
                f"Indice (base 100 en 2020): {row['valeur']}, "
                f"Qualite: {row['qualite']}"
            )
            documents.append({
                "text": text,
                "source": csv_path.name,
                "row": int(idx),
                "doc_type": "csv",
            })
    return documents


# ---------------------------------------------------------------------------
# Main ingest pipeline
# ---------------------------------------------------------------------------
def main():
    print("Loading and chunking PDFs (Docling)...")
    pdf_chunks_raw = load_pdfs_with_docling(PDF_DIR)
    print(f"Produced {len(pdf_chunks_raw)} PDF chunks.")

    print("Loading CSV rows...")
    csv_paths = _find_csv(AGRESTE_DIR)
    print(f"Found {len(csv_paths)} CSV file(s): {[p.name for p in csv_paths]}")
    csv_docs = load_csv(csv_paths)
    print(f"Loaded {len(csv_docs)} CSV rows total.")

    chunks = []
    metadatas = []

    # PDF chunks are already chunked by Docling - use as-is.
    for doc in pdf_chunks_raw:
        chunks.append(doc["text"])
        meta = {"source": doc["source"], "doc_type": "pdf"}
        if doc.get("page") is not None:
            meta["page"] = doc["page"]
        metadatas.append(meta)

    # CSV rows still go through the simple character chunker.
    for doc in csv_docs:
        for piece in chunk_text(doc["text"]):
            chunks.append(piece)
            metadatas.append({"source": doc["source"], "row": doc["row"], "doc_type": "csv"})

    print(f"Total chunks to embed: {len(chunks)}")

    if not chunks:
        print("No chunks to ingest. Check your source paths in ingest.py.")
        return

    # Reset the collection so old (incompatible) embeddings never linger.
    try:
        chroma_client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = chroma_client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    print("Embedding + storing chunks (runs locally, no API calls)...")
    for i in tqdm(range(0, len(chunks), EMBED_BATCH_SIZE)):
        batch_texts = chunks[i:i + EMBED_BATCH_SIZE]
        batch_meta = metadatas[i:i + EMBED_BATCH_SIZE]
        batch_ids = [str(uuid.uuid4()) for _ in batch_texts]

        embeddings = embed_model.encode(batch_texts, show_progress_bar=False).tolist()

        collection.add(
            ids=batch_ids,
            embeddings=embeddings,
            documents=batch_texts,
            metadatas=batch_meta,
        )

    print(f"Done. Collection '{COLLECTION_NAME}' now has {collection.count()} vectors.")


if __name__ == "__main__":
    main()