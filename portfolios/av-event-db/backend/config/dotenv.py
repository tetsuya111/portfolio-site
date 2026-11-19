"""backend/.env を読み込んで環境変数に設定する（依存を増やさない簡易版）。

- `KEY=VALUE` の形式。空行と `#` で始まる行は無視する
- 値の前後の空白と、値全体を囲む `"` または `'` は取り除く
- すでに設定されている環境変数は上書きしない（シェルでの指定を優先する）
"""

from collections.abc import MutableMapping
from pathlib import Path


def parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def load_env_file(path: Path, environ: MutableMapping[str, str]) -> None:
    if not path.is_file():
        return
    for key, value in parse_env(path.read_text(encoding="utf-8")).items():
        environ.setdefault(key, value)
