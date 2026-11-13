"""portfolio-site に掲載するポートフォリオの md（src/content/portfolios/<スラッグ>.md）の作成。"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)
_KEY = re.compile(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$")
_HTTP = re.compile(r"^https?://\S+$")


def _scalar(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        try:
            return json.loads(raw)
        except ValueError:
            return raw[1:-1]
    if len(raw) >= 2 and raw[0] == raw[-1] == "'":
        return raw[1:-1].replace("''", "'")
    return raw


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """`key: value` と `- 項目`・`[a, b]` のリストだけを扱う簡易パーサー。"""
    m = _FRONTMATTER.match(text)
    if not m:
        return {}, text
    data: dict = {}
    current: str | None = None
    for line in m.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current is not None:
            # 値なしのキーの直後に「- 項目」が続いたらリストとして扱う
            if data.get(current) == "":
                data[current] = []
            if isinstance(data.get(current), list):
                data[current].append(_scalar(stripped[2:]))
            continue
        km = _KEY.match(line)
        if not km:
            continue
        current, value = km.group(1), km.group(2).strip()
        if value.startswith("[") and value.endswith("]"):
            data[current] = [_scalar(v) for v in value[1:-1].split(",") if v.strip()]
        else:
            data[current] = _scalar(value)
    return data, text[m.end():]


def _drop_leading_h1(body: str) -> str:
    body = body.lstrip("\r\n")
    if body.startswith("# "):
        body = body.split("\n", 1)[1] if "\n" in body else ""
    return body.lstrip("\r\n")


def _split_title(text: str) -> tuple[str | None, str]:
    """コードブロック外の最初の `# 見出し` をタイトルとして取り出し、本文からその行を除く。"""
    lines = text.splitlines(keepends=True)
    fence: str | None = None
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith(("```", "~~~")):
            if fence is None:
                fence = s[:3]
            elif s.startswith(fence):
                fence = None
            continue
        if fence is None and line.startswith("# "):
            body = "".join(lines[:i] + lines[i + 1 :])
            return line[2:].strip() or None, body.lstrip("\r\n")
    return None, text


def _readme(project: Path) -> tuple[str | None, str]:
    for name in ("README.md", "readme.md", "Readme.md"):
        p = project / name
        if p.is_file():
            return _split_title(p.read_text(encoding="utf-8", errors="replace"))
    return None, ""


def write_portfolio_md(slug: str, project: Path, repo_root: Path, tags: list[str], app_url: str | None,
                       today: date) -> tuple[Path | None, list[str]]:
    out = repo_root / "portfolio-site" / "src" / "content" / "portfolios" / f"{slug}.md"
    if out.exists():
        return None, [f"{out.name} が既にあるため、掲載用の md を作成しませんでした"]

    docs = repo_root / "portfolios" / "docs" / f"{slug}.md"
    meta: dict = {}
    if docs.is_file():
        meta, body = parse_frontmatter(docs.read_text(encoding="utf-8", errors="replace"))
        body = _drop_leading_h1(body)
        title = meta.get("title") if isinstance(meta.get("title"), str) and meta.get("title") else None
    else:
        title, body = _readme(project)
    title = title or slug
    doc_tags = [t for t in meta.get("tags", []) if isinstance(t, str) and t] if isinstance(meta.get("tags"), list) else []
    final_tags = doc_tags or tags
    url = app_url or (meta.get("url") if isinstance(meta.get("url"), str) else None)
    if url and not _HTTP.match(url):
        url = None
    if not body.strip():
        body = "## 概要\n\n（ここにポートフォリオの説明を書く）\n"
    if not body.endswith("\n"):
        body += "\n"

    lines = ["---", f"title: {json.dumps(title, ensure_ascii=False)}"]
    if final_tags:
        lines.append("tags:")
        lines += [f"  - {json.dumps(t, ensure_ascii=False)}" for t in final_tags]
    if url:
        lines.append(f"url: {json.dumps(url, ensure_ascii=False)}")
    lines += [f"date: {today.isoformat()}", "---", "", ""]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + body, encoding="utf-8", newline="\n")
    return out, []
