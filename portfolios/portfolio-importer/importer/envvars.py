"""フロントエンド・バックエンドが読む環境変数名の探索と、サイトの URL の決定。

名前・URL の規則は portfolio-site/src/lib/apps-manifest.ts（apps.json の検証）と揃える。
照合は JavaScript の正規表現と同じ結果になるよう、すべて fullmatch で行う（re.match の $ は末尾の改行を許すため）。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from importer.ignore import iter_files

# apps.json の env に書ける名前・値（apps-manifest.ts の PUBLIC_ENV_NAME・HTTPS_URL と同じ）
PUBLIC_ENV_NAME = re.compile(r"(VITE_|PUBLIC_|NEXT_PUBLIC_)[A-Z0-9_]+")
HTTPS_URL = re.compile(r"https://[A-Za-z0-9.-]+(:[0-9]{1,5})?(/[A-Za-z0-9._~/-]*)?")
# Dockerfile の ENV に書ける URL（引用符などを含まない）
_SAFE_URL = re.compile(r"https?://[A-Za-z0-9.-]+(:[0-9]{1,5})?(/[A-Za-z0-9._~/-]*)?")
_DOMAIN = re.compile(r"(?=.{1,253}\Z)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", re.IGNORECASE)

_FRONTEND_EXTS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".vue", ".svelte", ".astro"}
_BACKEND_EXTS = {".py", ".js", ".ts", ".mjs", ".cjs"}
# 公開用の名前は接頭辞で区別できるため、参照の書き方（.X・["X"]・分割代入）によらず名前そのものを拾う
_FRONTEND_REF = re.compile(r"\b((?:VITE_|PUBLIC_|NEXT_PUBLIC_)[A-Z0-9_]+)\b")
_BACKEND_REF = re.compile(r"""os\.environ\.get\(\s*["']([A-Z][A-Z0-9_]*)["']"""
                          r"""|os\.environ\[\s*["']([A-Z][A-Z0-9_]*)["']"""
                          r"""|os\.getenv\(\s*["']([A-Z][A-Z0-9_]*)["']"""
                          r"""|process\.env\.([A-Z][A-Z0-9_]*)"""
                          r"""|process\.env\[\s*["']([A-Z][A-Z0-9_]*)["']""")
_ENV_EXAMPLE_LINE = re.compile(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=", re.MULTILINE)


# バックエンドの場所を表す語。先にあるものほど URL そのものを表すとみなし、候補の順位に使う
_LOCATION_WORDS = ["URL", "ORIGIN", "ENDPOINT", "HOST", "BASE"]


def _words(name: str) -> list[str]:
    # FIREBASE の BASE・GHOST の HOST などに当たらないよう、_ 区切りの語で比べる
    return name.split("_")


def _is_backend_url_name(name: str) -> bool:
    # VITE_API_KEY など URL でない変数を除くため、場所を表す語との組み合わせにする
    words = _words(name)
    return (PUBLIC_ENV_NAME.fullmatch(name) is not None and any(w in ("API", "BACKEND", "SERVER") for w in words)
            and any(w in _LOCATION_WORDS for w in words))


def _backend_url_rank(name: str) -> tuple[int, str]:
    # 末尾の語が場所を表す名前（VITE_API_URL）を、途中にあるもの（VITE_API_BASE_PATH）より先にする
    last = _words(name)[-1]
    return (_LOCATION_WORDS.index(last) if last in _LOCATION_WORDS else len(_LOCATION_WORDS), name)


def _is_origin_name(name: str) -> bool:
    # ORIGINAL_* などに当たらないよう語で比べる
    return any(w in ("ORIGIN", "ORIGINS") for w in _words(name))


def _is_frontend_url_name(name: str) -> bool:
    # 公開用の名前（VITE_API_ORIGIN など）はフロントエンド向けのため除く
    if PUBLIC_ENV_NAME.fullmatch(name):
        return False
    if _is_origin_name(name):
        return True
    words = _words(name)
    # SPOTIFY_CLIENT_ID・OAUTH_CLIENT_CALLBACK_URL など別の用途の変数を除くため、FRONTEND_URL・CLIENT_URL の並びに限る
    return any(a in ("FRONTEND", "CLIENT") and b == "URL" for a, b in zip(words, words[1:]))


def _is_test(rel: Path) -> bool:
    name = rel.name
    return (any(part in ("tests", "test", "__tests__") for part in rel.parts[:-1]) or name.startswith("test_")
            or re.search(r"\.(test|spec)\.[^.]+$", name) is not None or re.search(r"_test\.py$", name) is not None)


def _scan(d: Path, exts: set[str], ref: re.Pattern, skip_tests: bool,
          skip_dirs: list[Path] | None = None) -> set[str]:
    skip = {p.relative_to(d).as_posix() for p in (skip_dirs or []) if d in p.parents}
    names: set[str] = set()
    for rel in iter_files(d, skip_dirs=skip):
        if skip_tests and _is_test(rel):
            continue
        if rel.name == ".env.example":
            pattern = _ENV_EXAMPLE_LINE
        elif rel.suffix in exts:
            pattern = ref
        else:
            continue
        text = (d / rel).read_text(encoding="utf-8", errors="replace")
        for m in pattern.finditer(text):
            names.add(next(g for g in m.groups() if g))
    return names


def find_frontend_env_names(d: Path, skip_dirs: list[Path] | None = None) -> list[str]:
    """フロントエンドがバックエンドの URL として読んでいそうな公開用の環境変数名を、URL らしい順（同順位は名前順）で返す。

    skip_dirs（フロントエンド内にあるバックエンドなど）は探さない。
    """
    names = _scan(d, _FRONTEND_EXTS, _FRONTEND_REF, skip_tests=False, skip_dirs=skip_dirs)
    return sorted((n for n in names if _is_backend_url_name(n)), key=_backend_url_rank)


def find_backend_env_names(d: Path, skip_dirs: list[Path] | None = None) -> list[str]:
    """バックエンドがフロントエンドの URL（CORS の許可オリジンなど）として読んでいそうな環境変数名を、名前順で返す。

    skip_dirs（バックエンド内にあるフロントエンドなど）は探さない。
    """
    return sorted(n for n in _scan(d, _BACKEND_EXTS, _BACKEND_REF, skip_tests=True, skip_dirs=skip_dirs)
                  if _is_frontend_url_name(n))


def read_site_url(repo_root: Path) -> str | None:
    """portfolio-site/infra/parameters.json の DomainName から https://<ドメイン> を返す。判定できなければ None。"""
    path = repo_root / "portfolio-site" / "infra" / "parameters.json"
    try:
        # Windows のエディタ・PowerShell が付ける BOM があっても読めるようにする
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    params = data.get("Parameters") if isinstance(data, dict) else None
    domain = params.get("DomainName") if isinstance(params, dict) else None
    if not isinstance(domain, str) or not _DOMAIN.fullmatch(domain):
        return None
    return f"https://{domain.lower()}"


def frontend_url_env(names: list[str], site_url: str, slug: str, registered: bool) -> dict[str, str]:
    """各名前に、ORIGIN を含むならサイトのオリジン、それ以外は配信登録したならアプリの URL
    （<サイトの URL>/apps/<スラッグ>/。掲載 md の url と同じ）、しなかったならオリジンを入れる。

    Dockerfile に安全に書けない値になる場合は空の dict を返す。
    """
    parts = urlsplit(site_url)
    origin = f"{parts.scheme}://{parts.netloc}"
    app_url = f"{site_url.rstrip('/')}/apps/{slug}/"
    env = {n: origin if _is_origin_name(n) or not registered else app_url for n in names}
    return env if all(_SAFE_URL.fullmatch(v) for v in env.values()) else {}
