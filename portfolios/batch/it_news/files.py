"""既存記事の読み込み・出典 URL の重複判定・ファイル名の決定。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

MAX_NAME_LENGTH = 64
MAX_RECENT_TITLES = 30
FALLBACK_SLUG = "it-news"


@dataclass
class Existing:
    names: set[str] = field(default_factory=set)
    source_urls: set[str] = field(default_factory=set)
    recent_titles: list[str] = field(default_factory=list)


def normalize_url(url: str) -> str:
    """同じページを指す URL を同じ文字列にする（https に統一・ホストの小文字化・www. と # と utm_* と末尾 / を除く）。"""
    parts = urlsplit(url.strip())
    host = parts.netloc.lower().removeprefix("www.")
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not k.startswith("utm_")))
    path = parts.path.rstrip("/")
    return urlunsplit(("https", host, path, query, ""))


def _parse_value(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith('"'):
        try:
            return str(json.loads(raw))
        except ValueError:
            return raw.strip('"')
    if raw.startswith("'") and raw.endswith("'") and len(raw) >= 2:
        return raw[1:-1].replace("''", "'")
    return raw


def _frontmatter(text: str) -> dict[str, str]:
    """frontmatter の「キー: 値」の1行のものだけを読む（title・date・sourceUrl に十分な簡易版）。"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    data: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m and m.group(2):
            data[m.group(1)] = _parse_value(m.group(2))
    return data


def load_existing(dirs: list[Path]) -> Existing:
    """フォルダ内の *.md を読む。存在しないフォルダは空として扱う。"""
    ex = Existing()
    dated: list[tuple[str, str, str]] = []
    for d in dirs:
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.md")):
            ex.names.add(p.stem)
            fm = _frontmatter(p.read_text(encoding="utf-8"))
            if fm.get("sourceUrl"):
                ex.source_urls.add(normalize_url(fm["sourceUrl"]))
            if fm.get("title"):
                dated.append((fm.get("date", ""), p.stem, fm["title"]))
    dated.sort(reverse=True)
    ex.recent_titles = [t for _, _, t in dated[:MAX_RECENT_TITLES]]
    return ex


def _clean_slug(slug: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")
    return s or FALLBACK_SLUG


def _fit(base: str, suffix: str) -> str:
    return base[: MAX_NAME_LENGTH - len(suffix)].rstrip("-") + suffix


def choose_file_name(date: str, slug: str, taken: set[str]) -> str:
    """`YYYY-MM-DD-<slug>`（拡張子なし、64 文字以内）。taken と重なれば -2、-3 … を付ける。"""
    base = f"{date}-{_clean_slug(slug)}"
    name = _fit(base, "")
    n = 2
    while name in taken:
        name = _fit(base, f"-{n}")
        n += 1
    return name
