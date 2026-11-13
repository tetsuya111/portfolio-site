"""テスト用の補助関数。"""

import json
import tempfile
from pathlib import Path


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
