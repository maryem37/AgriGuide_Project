"""Compatibility patches applied before third-party imports that need them."""
try:
    import pdfminer.pdfparser as _pdfparser

    if not hasattr(_pdfparser, "PSSyntaxError"):
        _pdfparser.PSSyntaxError = _pdfparser.PDFSyntaxError  # type: ignore[attr-defined]
except Exception:
    pass
