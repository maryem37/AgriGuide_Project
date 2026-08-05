"""Derive public source URLs for RAG corpus documents."""
import re

# Filenames from fetch_hal_documents.py are `{halId}_{slug}.pdf`
# (e.g. hal-01685936_Risques_....pdf, tel-01229768_....pdf).
HAL_ID_RE = re.compile(
    r"^(?P<hal_id>(?:hal|tel|medihal|pastel|mem|ijn|inserm|cea|ird)-\d+)",
    re.IGNORECASE,
)


def source_url_for_document(source_document: str, explicit_url: str | None = None) -> str | None:
    """Return a public HAL landing-page URL when one can be derived."""
    if explicit_url and explicit_url.startswith("http"):
        return explicit_url
    name = (source_document or "").rsplit("/", 1)[-1]
    match = HAL_ID_RE.match(name)
    if not match:
        return None
    return f"https://hal.science/{match.group('hal_id')}"
