"""
PDF parser agent (secondary, optional input path).

Uploaded PDFs are not the primary knowledge source in this system (the
researcher agent's autonomous web/academic search is), but the system
still supports feeding a PDF in when the user has one worth including.
Extracted text chunks are wrapped as SearchResult objects with
source_type=UPLOADED_PDF so they flow through the exact same
extractor/validator pipeline as web/academic sources.
"""
from __future__ import annotations

from pathlib import Path

from config.logging_config import get_logger
from models import SearchResult, SourceType

logger = get_logger(__name__)

# Roughly one "page-sized" chunk per extraction call, matching the level of
# granularity the extraction prompt is tuned for (short, focused passages).
CHUNK_CHAR_SIZE = 3000
CHUNK_OVERLAP = 200


class PDFParserAgent:
    """Extracts text from an uploaded PDF and chunks it into SearchResult objects."""

    def parse(self, pdf_path: str, title_hint: str = "") -> list[SearchResult]:
        try:
            import pypdf
        except ImportError as e:
            raise RuntimeError("The 'pypdf' package is required to parse PDFs. Install it with: pip install pypdf") from e

        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        title = title_hint or path.stem
        reader = pypdf.PdfReader(str(path))

        results: list[SearchResult] = []
        for page_num, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as e:  # noqa: BLE001
                logger.warning("Failed to extract text from page %d of %s: %s", page_num, path.name, e)
                continue

            text = text.strip()
            if len(text) < 40:
                continue

            for chunk in _chunk_text(text):
                results.append(
                    SearchResult(
                        source_type=SourceType.UPLOADED_PDF,
                        title=f"{title} (page {page_num})",
                        url=None,
                        snippet=chunk[:500],
                        full_text=chunk,
                    )
                )

        logger.info("Parsed '%s': %d chunks extracted from %d pages.", path.name, len(results), len(reader.pages))
        return results


def _chunk_text(text: str, size: int = CHUNK_CHAR_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks
