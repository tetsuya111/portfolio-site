"""設定ファイル config.json（バックエンドを公開するドメインと HTTPS の有無）の読み込み。"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from stackgen import StackError

_HOST = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$")
# 例のドメインのまま nginx の設定やフロントエンドの URL を作らない
_EXAMPLE = re.compile(r"(?:^|\.)example\.(?:com|org|net)$")


@dataclass(frozen=True)
class Config:
    domain: str
    https: bool


def load_config(path: Path) -> Config:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise StackError(f"設定ファイル {path.name} を読めません: {e}") from e
    except ValueError as e:
        raise StackError(f"設定ファイル {path.name} を JSON として読めません: {e}") from e
    if not isinstance(data, dict):
        raise StackError(f'{path.name} は {{"domain": ..., "https": ...}} の形にしてください')
    domain = data.get("domain")
    if not isinstance(domain, str) or not _HOST.match(domain.lower()):
        raise StackError(f"{path.name} の domain にはホスト名（例 api.your-domain.com）を書いてください")
    domain = domain.lower()
    if _EXAMPLE.search(domain):
        raise StackError(f"{path.name} の domain が例（{domain}）のままです。バックエンドを公開するドメインに書き換えてください")
    https = data.get("https", True)
    if not isinstance(https, bool):
        raise StackError(f"{path.name} の https は true か false にしてください")
    return Config(domain, https)
