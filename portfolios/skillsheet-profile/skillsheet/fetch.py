"""URL のスキルシートを取得する。Google スプレッドシートは公開シートを xlsx でエクスポートする（OAuth は扱わない）。"""

import re
import urllib.error
import urllib.request

from skillsheet import readers
from skillsheet.errors import SkillsheetError

TIMEOUT_SECONDS = 30
_SHEET_RE = re.compile(r"^https://docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]+)")
_PRIVATE_MESSAGE = (
    "スプレッドシートを取得できません（非公開の可能性があります）。"
    "共有設定を「リンクを知っている全員」にするか、xlsx か csv でダウンロードしてファイルを指定してください"
)


def is_url(source: str) -> bool:
    """http(s) の URL か。"""
    return re.match(r"^https?://", source, re.IGNORECASE) is not None


def has_scheme(source: str) -> bool:
    """`<スキーム>://` で始まるか（ファイルパスとして扱わないもの）。"""
    return re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", source) is not None


def to_export_url(url: str) -> str | None:
    """Google スプレッドシートの URL なら xlsx のエクスポート URL を返す。それ以外は None。"""
    m = _SHEET_RE.match(url)
    return f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=xlsx" if m else None


def fetch(url: str, opener=urllib.request.urlopen) -> tuple[bytes, str]:
    """URL を取得し、(本文, 読み分けに使う拡張子) を返す。"""
    if not is_url(url):
        raise SkillsheetError(f"http(s) 以外の URL は使えません: {url}")
    export = to_export_url(url)
    request = urllib.request.Request(export or url, headers={"User-Agent": "skillsheet-profile"})
    try:
        with opener(request, timeout=TIMEOUT_SECONDS) as res:
            content_type = res.headers.get_content_type()
            body = res.read(readers.MAX_BYTES + 1)
    except urllib.error.HTTPError as e:
        if export and e.code in (401, 403, 404):
            raise SkillsheetError(_PRIVATE_MESSAGE) from None
        raise SkillsheetError(f"URL を取得できません（HTTP {e.code}）: {url}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise SkillsheetError(f"URL を取得できません（{e}）: {url}") from None
    if len(body) > readers.MAX_BYTES:
        raise SkillsheetError(f"応答が大きすぎます（上限 {readers.MAX_BYTES // (1024 * 1024)}MB）: {url}")
    if export:
        if content_type == "text/html":
            # 非公開シートはログイン画面の HTML が返る
            raise SkillsheetError(_PRIVATE_MESSAGE)
        return body, ".xlsx"
    return body, ".html"
