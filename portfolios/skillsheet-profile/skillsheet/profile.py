"""profile.md の下書きを検証し、置き換える。

frontmatter は portfolio-site の profileSchema（portfolio-site/src/lib/schemas.ts）と同じ規則で検証する。
汎用の YAML パーサーではなく、profile.md の形（トップレベルの key: value と links の並び）だけを解釈する。
スキーマが変わったらここも直すこと。
"""

import json
import os
import re
import tempfile
from pathlib import Path

# このファイルは <リポジトリ>/portfolios/skillsheet-profile/skillsheet/ にある
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TARGET = REPO_ROOT / "portfolio-site" / "src" / "content" / "profile" / "profile.md"

REQUIRED_HEADINGS = ("## 自己紹介", "## 経歴", "## スキル")
_TOP = re.compile(r"^([A-Za-z_][\w-]*):(?:\s+(.*))?$")
_ITEM_START = re.compile(r"^\s+-\s+([A-Za-z_][\w-]*):(?:\s+(.*))?$")
_ITEM_CONT = re.compile(r"^\s+([A-Za-z_][\w-]*):(?:\s+(.*))?$")
# クォートなしだと YAML で文字列以外（数値・真偽値・null・日付）になる値
_NON_STRING = re.compile(
    r"^(?:[-+]?(?:\d[\d_]*)?\.?\d+(?:[eE][-+]?\d+)?|0x[0-9a-fA-F]+|0o[0-7]+|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN)"
    r"|true|True|TRUE|false|False|FALSE|null|Null|NULL|~|\d{4}-\d{2}-\d{2}(?:[Tt ].*)?)$"
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
    if ": " in raw or raw.endswith(":") or " #" in raw:
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
    for no, line in enumerate(lines, start=2):  # 1 行目は ---
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key = None
        try:
            if not line[0].isspace():
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
                    continue
                data[key] = _scalar(raw)
                continue
            if links is None:
                raise _ScalarError("インデントされた行は links の中にだけ書けます")
            m = _ITEM_START.match(line)
            if m:
                links.append({})
            else:
                m = _ITEM_CONT.match(line)
                if not m or not links:
                    raise _ScalarError("links の要素は「- label: ...」で始めてください")
            key, raw = m.group(1), m.group(2)
            if key in links[-1]:
                raise _ScalarError(f"links の {key} が重複しています")
            key = f"links.{len(links) - 1}.{key}"
            links[-1][m.group(1)] = _scalar(raw)
        except _ScalarError as e:
            where = f"（{key}）" if key else ""
            errors.append(f"frontmatter の {no} 行目{where}を解釈できません: {e}")
    return data


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
        url = link.get("url")
        if not isinstance(url, str) or not re.match(r"^https?://\S+$", url):
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
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
