"""テストから portfolio-importer のモジュール（検出・コピー）を使えるようにする（add_backend.py と同じ）。"""

import sys
from pathlib import Path

_IMPORTER = Path(__file__).resolve().parent.parent.parent / "portfolio-importer"
if str(_IMPORTER) not in sys.path:
    sys.path.insert(0, str(_IMPORTER))
