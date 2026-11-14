"""profile.md の下書きを検証し、置き換える。

frontmatter は portfolio-site の profileSchema（portfolio-site/src/lib/schemas.ts）と同じ規則で検証する。
汎用の YAML パーサーではなく、profile.md の形（トップレベルの key: value と links の並び）だけを解釈する。
スキーマが変わったらここも直すこと。
"""

import json
import os
import re
import stat
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

# このファイルは <リポジトリ>/portfolios/skillsheet-profile/skillsheet/ にある
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TARGET = REPO_ROOT / "portfolio-site" / "src" / "content" / "profile" / "profile.md"

REQUIRED_HEADINGS = ("## 自己紹介", "## 経歴", "## スキル")
_TOP = re.compile(r"^([A-Za-z_][\w-]*):(?:\s+(.*))?$")
# YAML のインデントは空白だけ（タブは不可）。group(1)=「-」までの空白、group(2)=キー、group(3)=値
_ITEM_START = re.compile(r"^( *)- +([A-Za-z_][\w-]*):(?: +(.*))?$")
_ITEM_CONT = re.compile(r"^( +)([A-Za-z_][\w-]*):(?: +(.*))?$")
# クォートなしだと YAML（js-yaml・yaml の両方）で文字列以外（数値・真偽値・null・日付）になりうる値。
# 文字列として扱われるものまで含めて広めに拒否する（クォートすれば必ず通る）。
_NON_STRING = re.compile(
    r"^(?:[-+]?[\d_]*\.?[\d_]+(?:[eE][-+]?\d+)?|[-+]?0b[01_]+|[-+]?0x[0-9a-fA-F_]+|[-+]?0o[0-7_]+"
    r"|[-+]?\d[\d_]*(?::[0-5]?\d)+(?:\.[\d_]*)?|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN)"
    r"|true|True|TRUE|false|False|FALSE|yes|Yes|YES|no|No|NO|on|On|ON|off|Off|OFF|y|Y|n|N"
    r"|null|Null|NULL|~|\d{4}-\d{1,2}-\d{1,2}(?:(?:[Tt]|\s+).*)?)$"
)
# クォートなしでは YAML の別の構文になる先頭の記号
_SPECIAL_START = tuple("[]{}|>&*!%@`#,?-")


class _ScalarError(ValueError):
    pass


def _scalar(raw: str | None) -> str | None:
    """YAML のスカラーを文字列にする。None は値なし（YAML の null）。"""
    raw = (raw or "").strip()
    if raw == "":
        return None
    if raw.startswith('"'):
        if len(raw) < 2 or not raw.endswith('"'):
            raise _ScalarError("ダブルクォートが閉じていません")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            raise _ScalarError("ダブルクォートの中身を解釈できません") from None
        return value
    if raw.startswith("'"):
        if len(raw) < 2 or not raw.endswith("'") or re.search(r"(?<!')'(?!')", raw[1:-1]):
            raise _ScalarError("シングルクォートが閉じていません")
        return raw[1:-1].replace("''", "'")
    if raw.startswith(_SPECIAL_START):
        raise _ScalarError(f"記号 {raw[0]} で始まる値はダブルクォートで囲んでください")
    if re.search(r":\s|\s#", raw) or raw.endswith(":"):
        raise _ScalarError("値に「: 」「 #」を含むときはダブルクォートで囲んでください")
    if _NON_STRING.match(raw):
        raise _ScalarError("数値・真偽値・日付として扱われるため、ダブルクォートで囲んでください")
    return raw


def _split(text: str) -> tuple[list[str], list[str]] | None:
    """(frontmatter の行, 本文の行) に分ける。frontmatter がなければ None。"""
    lines = text.lstrip("﻿").replace("\r\n", "\n").split("\n")
    if lines[0].rstrip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            return lines[1:i], lines[i + 1:]
    return None


def _parse_frontmatter(lines: list[str], errors: list[str]) -> dict:
    data: dict = {}
    links: list[dict] | None = None  # links の並びを読んでいる間だけ list
    dash_col = key_col = None  # 要素の「-」の列と、要素内のキーの列（YAML ではすべての要素でそろう必要がある）
    bare_links = False  # 値なしの「links:」と書かれたか
    for no, line in enumerate(lines, start=2):  # 1 行目は ---
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key = None
        try:
            item = _ITEM_START.match(line) if links is not None else None
            if not line[0].isspace() and not item:
                links = None
                m = _TOP.match(line)
                if not m:
                    raise _ScalarError("「key: value」の形ではありません")
                key, raw = m.group(1), (m.group(2) or "").strip()
                if key in data:
                    raise _ScalarError(f"{key} が重複しています")
                if key == "links":
                    if raw not in ("", "[]"):
                        raise _ScalarError("links は「- label: ...」「url: ...」の並びで書いてください")
                    data[key] = []
                    links = data[key] if raw == "" else None
                    bare_links = raw == ""
                    dash_col = key_col = None
                    continue
                data[key] = _scalar(raw)
                continue
            if links is None:
                raise _ScalarError("インデントされた行は links の中にだけ書けます")
            if item:
                col_dash, col_key = len(item.group(1)), item.start(2)
                if dash_col is None:
                    dash_col, key_col = col_dash, col_key
                elif (col_dash, col_key) != (dash_col, key_col):
                    raise _ScalarError("links の要素のインデントがそろっていません")
                links.append({})
                name, raw = item.group(2), item.group(3)
            else:
                m = _ITEM_CONT.match(line)
                if not m or not links:
                    raise _ScalarError("links の要素は「- label: ...」で始めてください")
                if len(m.group(1)) != key_col:
                    raise _ScalarError("links の要素のインデントが「- 」の後ろのキーとそろっていません")
                name, raw = m.group(2), m.group(3)
            key = f"links.{len(links) - 1}.{name}"
            if name in links[-1]:
                raise _ScalarError(f"{name} が重複しています")
            links[-1][name] = _scalar(raw)
        except _ScalarError as e:
            where = f"（{key}）" if key else ""
            errors.append(f"frontmatter の {no} 行目{where}を解釈できません: {e}")
    if bare_links and not data.get("links"):
        # 値のない「links:」は YAML では null になり、スキーマ（配列か省略）に合わない
        errors.append("links: 要素がありません（リンクがなければ行ごと消してください）")
    return data


def _is_http_url(url) -> bool:
    """スキーマの z.url({ protocol: /^https?$/ }) に近い判定。ホスト名を持つ http(s) の URL だけを通す。"""
    if not isinstance(url, str) or not url or re.search(r"\s", url):
        return False
    try:
        parts = urlsplit(url)
        host = parts.hostname
        parts.port  # 不正なポートは ValueError
    except ValueError:
        return False
    if parts.scheme.lower() not in ("http", "https") or not host:
        return False
    # % を含むホスト名・使えない記号を含むホスト名は WHATWG URL でも不正になる
    return re.fullmatch(r"[A-Za-z0-9\-._~\u0080-\U0010ffff]+|\[[0-9A-Fa-f:.]+\]", host if ":" not in host else f"[{host}]") is not None


def validate(text: str) -> list[str]:
    """下書きを検証し、エラーの一覧を返す（空なら合格）。"""
    parts = _split(text)
    if parts is None:
        return ["先頭に --- で囲んだ frontmatter がありません"]
    fm_lines, body = parts
    errors: list[str] = []
    data = _parse_frontmatter(fm_lines, errors)

    for key in ("name", "role"):
        if not isinstance(data.get(key), str) or not data[key]:
            errors.append(f"{key}: 空でない文字列が必要です")
    if "summary" in data and not isinstance(data["summary"], str):
        errors.append("summary: 文字列が必要です（不要なら行ごと消してください）")
    for i, link in enumerate(data.get("links") or []):
        if not isinstance(link.get("label"), str) or not link["label"]:
            errors.append(f"links.{i}.label: 空でない文字列が必要です")
        if not _is_http_url(link.get("url")):
            errors.append(f"links.{i}.url: http:// か https:// で始まる URL が必要です")

    body_lines = {line.rstrip() for line in body}
    for heading in REQUIRED_HEADINGS:
        if heading not in body_lines:
            errors.append(f"本文に見出し「{heading}」がありません")
    return errors


def write_profile(text: str, target: Path) -> None:
    """検証済みの text で target を置き換える。一時ファイルに書いてから差し替える（途中で失敗しても壊さない）。"""
    target = Path(target)
    content = text.lstrip("﻿").replace("\r\n", "\n")
    if not content.endswith("\n"):
        content += "\n"
    fd, tmp = tempfile.mkstemp(prefix=".profile-", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        # mkstemp は 0600 で作るため、元のファイルのパーミッションを引き継ぐ（新規なら 0644）
        mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o644
        os.chmod(tmp, mode)
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
