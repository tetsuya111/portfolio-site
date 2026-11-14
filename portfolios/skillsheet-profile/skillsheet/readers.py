"""スキルシートのファイルをテキストにする。項目の解釈は行わない（R11）。"""

from pathlib import Path

from skillsheet.errors import SkillsheetError

MAX_BYTES = 20 * 1024 * 1024

TEXT_EXTS = {".txt", ".md", ".csv", ".tsv"}
HTML_EXTS = {".html", ".htm"}
XLSX_EXTS = {".xlsx", ".xlsm"}
DOCX_EXTS = {".docx"}
SUPPORTED_EXTS = TEXT_EXTS | HTML_EXTS | XLSX_EXTS | DOCX_EXTS

# 標準ライブラリで読めない形式と、保存し直す先の案内
_LEGACY_HINTS = {
    ".xls": "xlsx か csv で保存し直してください",
    ".ods": "xlsx か csv で保存し直してください",
    ".doc": "docx かテキストで保存し直してください",
}


def decode_text(data: bytes) -> str:
    """UTF-8（BOM 付きを含む）→ Shift_JIS（cp932）の順にデコードする。"""
    for encoding in ("utf-8-sig", "cp932"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise SkillsheetError("文字コードを判別できません（UTF-8 か Shift_JIS で保存してください）")


def read_bytes(data: bytes, ext: str) -> str:
    """拡張子 ext（小文字・ドット付き）に応じて data をテキストにする。"""
    if len(data) > MAX_BYTES:
        raise SkillsheetError(f"ファイルが大きすぎます（上限 {MAX_BYTES // (1024 * 1024)}MB）")
    if ext in TEXT_EXTS:
        return decode_text(data)
    if ext in HTML_EXTS:
        from skillsheet.html_text import html_to_text

        return html_to_text(decode_text(data))
    if ext in XLSX_EXTS:
        from skillsheet.office import xlsx_to_text

        return xlsx_to_text(data)
    if ext in DOCX_EXTS:
        from skillsheet.office import docx_to_text

        return docx_to_text(data)
    hint = _LEGACY_HINTS.get(ext, "対応形式: " + "・".join(sorted(SUPPORTED_EXTS)))
    raise SkillsheetError(f"対応していない形式です: {ext or '(拡張子なし)'}（{hint}）")


def read_file(path: Path) -> str:
    """ローカルファイルを読み、拡張子に応じてテキストにする。"""
    path = Path(path)
    if not path.is_file():
        raise SkillsheetError(f"ファイルが見つかりません: {path}")
    try:
        if path.stat().st_size > MAX_BYTES:
            raise SkillsheetError(f"ファイルが大きすぎます（上限 {MAX_BYTES // (1024 * 1024)}MB）: {path}")
        data = path.read_bytes()
    except OSError as e:
        raise SkillsheetError(f"ファイルを読めません（{e.strerror or e}）: {path}") from None
    return read_bytes(data, path.suffix.lower())
