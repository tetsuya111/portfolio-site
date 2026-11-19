"""取り込み対象サイトの抽出ルール（sources.json）の読み込みと検証（NFR-4）。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_SOURCES_PATH = Path(__file__).with_name("sources.json")
FIELD_NAMES = ("title", "actresses", "date", "venue", "address", "summary", "note", "link")
REQUIRED_FIELDS = ("title", "date")


class SourceConfigError(ValueError):
    """sources.json の内容が不正。"""


@dataclass(frozen=True)
class FieldRule:
    selector: str
    multiple: bool = False
    attr: str | None = None


@dataclass(frozen=True)
class SourceConfig:
    name: str
    list_urls: tuple[str, ...]
    mode: str
    fields: dict[str, FieldRule]
    detail_link_selector: str | None = None
    item_selector: str | None = None
    cookies: dict[str, str] = field(default_factory=dict)


def _field_rule(name: str, raw: Any) -> FieldRule:
    if isinstance(raw, str) and raw:
        return FieldRule(selector=raw)
    if isinstance(raw, dict) and isinstance(raw.get("selector"), str) and raw["selector"]:
        attr = raw.get("attr")
        if attr is not None and not isinstance(attr, str):
            raise SourceConfigError(f"fields.{name}.attr は文字列で指定してください。")
        return FieldRule(raw["selector"], bool(raw.get("multiple", False)), attr)
    raise SourceConfigError(f"fields.{name} にはセレクタを指定してください。")


def parse_source(raw: dict[str, Any]) -> SourceConfig:
    name = raw.get("name")
    if not isinstance(name, str) or not name:
        raise SourceConfigError("name は必須です。")
    list_urls = raw.get("list_urls")
    if not isinstance(list_urls, list) or not list_urls:
        raise SourceConfigError(f"{name}: list_urls を1件以上指定してください。")
    if not all(isinstance(u, str) and u.startswith(("http://", "https://")) for u in list_urls):
        raise SourceConfigError(f"{name}: list_urls は http(s) のURLで指定してください。")
    mode = raw.get("mode")
    if mode not in ("detail", "list"):
        raise SourceConfigError(f"{name}: mode は detail か list です。")
    raw_fields = raw.get("fields") or {}
    if not isinstance(raw_fields, dict):
        raise SourceConfigError(f"{name}: fields はオブジェクトで指定してください。")
    unknown = set(raw_fields) - set(FIELD_NAMES)
    if unknown:
        raise SourceConfigError(f"{name}: 未知のフィールド {sorted(unknown)}")
    for req in REQUIRED_FIELDS:
        if req not in raw_fields:
            raise SourceConfigError(f"{name}: fields.{req} は必須です。")
    fields = {k: _field_rule(k, v) for k, v in raw_fields.items()}
    detail_sel = raw.get("detail_link_selector")
    item_sel = raw.get("item_selector")
    if mode == "detail" and not detail_sel:
        raise SourceConfigError(f"{name}: detail モードでは detail_link_selector が必須です。")
    if mode == "list" and not item_sel:
        raise SourceConfigError(f"{name}: list モードでは item_selector が必須です。")
    cookies = raw.get("cookies") or {}
    if not isinstance(cookies, dict):
        raise SourceConfigError(f"{name}: cookies はオブジェクトで指定してください。")
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in cookies.items()):
        raise SourceConfigError(f"{name}: cookies は文字列の対応で指定してください。")
    return SourceConfig(
        name=name,
        list_urls=tuple(list_urls),
        mode=mode,
        fields=fields,
        detail_link_selector=detail_sel,
        item_selector=item_sel,
        cookies=dict(cookies),
    )


def load_sources(path: Path | None = None) -> list[SourceConfig]:
    data = json.loads((path or DEFAULT_SOURCES_PATH).read_text(encoding="utf-8"))
    sources = [parse_source(s) for s in data.get("sources", [])]
    names = [s.name for s in sources]
    if len(names) != len(set(names)):
        raise SourceConfigError("name が重複しています。")
    return sources
