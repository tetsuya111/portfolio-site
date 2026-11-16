"""配信するフロントエンド（portfolio-site/apps/<スラッグ>/）に、バックエンドの URL を渡す。

portfolio-site/apps/apps.json の項目の env（ビルド時の環境変数）に URL を書き、mock を false（実 API）にする。
名前と値の規則は portfolio-site の validateManifest（src/lib/apps-manifest.ts）と同じにする。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from importer.ignore import iter_files
from stackgen import StackError
from stackgen.config import Config

SOURCE_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".vue", ".svelte", ".astro"}
_PUBLIC_NAME = re.compile(r"\b(?:VITE_|PUBLIC_|NEXT_PUBLIC_)[A-Z0-9_]+\b")
_URL_WORDS = (re.compile(r"API|BACKEND|SERVER"), re.compile(r"URL|ORIGIN|BASE|ENDPOINT|HOST"))
ENV_VALUE = re.compile(r"^https://[A-Za-z0-9.\-_~/:%]+$")
_BUILD_DIRS = {"dist", "out", "build", ".next", ".astro"}


def backend_url(cfg: Config, slug: str) -> str:
    return f"{'https' if cfg.https else 'http'}://{cfg.domain}/{slug}"


def find_env_names(app_dir: Path) -> list[str]:
    """フロントエンドのソースと .env.example から、バックエンドの URL を入れる公開用の環境変数名を名前順で返す。"""
    names: set[str] = set()
    for rel in iter_files(app_dir, skip_dirs=_BUILD_DIRS):
        if rel.suffix not in SOURCE_SUFFIXES and rel.name != ".env.example":
            continue
        text = (app_dir / rel).read_text(encoding="utf-8", errors="replace")
        names.update(n for n in _PUBLIC_NAME.findall(text) if all(w.search(n) for w in _URL_WORDS))
    return sorted(names)


def update_apps_json(repo_root: Path, slug: str, url: str) -> tuple[dict | None, list[str]]:
    """apps.json の slug の項目に env を書いて mock を false にする。書いた env と警告を返す。

    apps.json がない・slug が登録されていなければ何もしない（フロントエンドを配信していない）。
    """
    apps = repo_root / "portfolio-site" / "apps"
    manifest = apps / "apps.json"
    if not manifest.is_file():
        return None, []
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except ValueError as e:
        raise StackError(f"apps.json を JSON として読めません: {e}") from e
    entries = data.get("apps") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise StackError('apps.json の形式が不正です（{"apps": [...]} が必要です）')
    entry = next((e for e in entries if isinstance(e, dict) and e.get("slug") == slug), None)
    if entry is None:
        return None, []

    if not ENV_VALUE.match(url):
        return None, [f"バックエンドの URL {url} が https ではないため、フロントエンドはモックのままにしました"
                      "（サイトは HTTPS のため http の API は呼べません）。config.json の https を true にしてください"]
    names = find_env_names(apps / slug)
    if not names:
        return None, ["フロントエンドのソースからバックエンドの URL を読む環境変数（VITE_API_URL など）が見つからないため、"
                      f'モックのままにしました。使う場合は apps.json の {slug} に "env": {{"<名前>": "{url}"}}'
                      ' と "mock": false を書いてください']
    name, others = names[0], names[1:]
    warnings = []
    if others:
        warnings.append(f"環境変数の候補が複数あるため {name} に URL を設定しました。ほかの候補: {', '.join(others)}")
    env = entry.get("env") if isinstance(entry.get("env"), dict) else {}
    if name in env and env[name] != url:
        warnings.append(f"apps.json の {slug} の env.{name} に別の値があるため上書きせず、モックの設定も変更しませんでした")
        return None, warnings
    env[name] = url
    entry["env"] = env
    entry["mock"] = False
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return {name: url}, warnings
