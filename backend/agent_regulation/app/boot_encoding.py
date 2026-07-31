"""Force UTF-8 sur stdout/stderr (Windows cp1252).

À importer en tout premier dans les points d'entrée pour éviter les
UnicodeEncodeError sur des caractères des textes légaux (ex. U+2015).
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
