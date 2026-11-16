"""テスト用の補助関数。"""

import json
import sys
import tempfile
from pathlib import Path

# portfolio-importer のモジュール（検出・コピー）を再利用する
IMPORTER = Path(__file__).resolve().parent.parent.parent / "portfolio-importer"
if str(IMPORTER) not in sys.path:
    sys.path.insert(0, str(IMPORTER))


class TempDirMixin:
    """各テストに一時ディレクトリ self.tmp を用意する。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name).resolve()

    def tearDown(self):
        self._tmp.cleanup()


def write(path: Path, text: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_json(path: Path, data) -> Path:
    return write(path, json.dumps(data))
