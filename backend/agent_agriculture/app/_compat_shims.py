"""
Compat shim for the unstructured[pdf]==0.15.13 / pdfminer.six version
mismatch (see requirements.txt for the full explanation of why
pdfminer.six is deliberately left unpinned instead of pinned to an old
version).

unstructured==0.15.13 does `from pdfminer.pdfparser import PSSyntaxError`.
Newer pdfminer.six releases removed that symbol from pdfparser (it now
lives in — or was folded into — pdfminer.psparser). Import THIS module
before importing anything from `unstructured`, so the symbol exists by
the time unstructured's own import runs.

Usage: `import app._compat_shims  # noqa: F401` as the first import in
any module that imports `unstructured`.
"""
import pdfminer.pdfparser as _pdfparser

if not hasattr(_pdfparser, "PSSyntaxError"):
    try:
        from pdfminer.psparser import PSSyntaxError as _PSSyntaxError
    except ImportError:
        class _PSSyntaxError(Exception):
            """Fallback stand-in if pdfminer.six ever drops this entirely."""

    _pdfparser.PSSyntaxError = _PSSyntaxError
