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


def _is_backend_url_name(name: str) -> bool:
    # VITE_API_KEY など URL でない変数を除くため、場所を表す語との組み合わせにする
    return (PUBLIC_ENV_NAME.fullmatch(name) is not None and re.search(r"API|BACKEND|SERVER", name) is not None
            and re.search(r"URL|ORIGIN|BASE|ENDPOINT|HOST", name) is not None)


def _is_frontend_url_name(name: str) -> bool:
    # 公開用の名前（VITE_API_ORIGIN など）はフロントエンド向けのため除く
    if PUBLIC_ENV_NAME.fullmatch(name):
        return False
    # SPOTIFY_CLIENT_ID など URL でない変数を除くため、CLIENT・FRONTEND は URL との組み合わせにする
    return "ORIGIN" in name or (re.search(r"FRONTEND|CLIENT", name) is not None and "URL" in name)


def _is_test(rel: Path) -> bool:
    return any(part in ("tests", "test") for part in rel.parts[:-1]) or rel.name.startswith("test_")


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


def find_frontend_env_names(d: Path) -> list[str]:
    """フロントエンドがバックエンドの URL として読んでいそうな公開用の環境変数名を、名前順で返す。"""
    return sorted(n for n in _scan(d, _FRONTEND_EXTS, _FRONTEND_REF, skip_tests=False) if _is_backend_url_name(n))


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
        data = json.loads(path.read_text(encoding="utf-8"))
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
    env = {n: origin if "ORIGIN" in n or not registered else app_url for n in names}
    return env if all(_SAFE_URL.fullmatch(v) for v in env.values()) else {}
