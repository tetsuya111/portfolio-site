"""xlsx・docx（Office Open XML）を標準ライブラリだけでテキストにする。"""

import io
import posixpath
import re
import zipfile
import zlib
from datetime import date, timedelta
from xml.etree import ElementTree as ET

from skillsheet import readers
from skillsheet.errors import SkillsheetError

_S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PR = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_MC_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"


class _Package:
    """zip を開き、展開後の合計サイズを上限と比べてから XML を読む（zip 爆弾の対策）。"""

    def __init__(self, data: bytes, kind: str):
        self.kind = kind
        try:
            self.zip = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            raise SkillsheetError(f"{kind} ファイルとして開けません（壊れているか、形式が違います）") from None
        total = sum(info.file_size for info in self.zip.infolist())
        if total > readers.MAX_BYTES:
            raise SkillsheetError(f"{kind} の展開後のサイズが大きすぎます（上限 {readers.MAX_BYTES // (1024 * 1024)}MB）")

    def has(self, name: str) -> bool:
        return name in self.zip.namelist()

    def xml(self, name: str) -> ET.Element:
        try:
            return ET.fromstring(self.zip.read(name))
        except KeyError:
            raise SkillsheetError(f"{self.kind} に {name} がありません（壊れているか、形式が違います）") from None
        except RuntimeError:
            # zipfile は暗号化されたメンバーで RuntimeError を出す
            raise SkillsheetError(f"{self.kind} がパスワードで保護されています（保護を外して保存し直してください）") from None
        except (ET.ParseError, zipfile.BadZipFile, zlib.error, NotImplementedError, EOFError, OSError):
            raise SkillsheetError(f"{self.kind} の {name} を読めません（壊れているか、未対応の圧縮形式です）") from None


def _string_item(el: ET.Element) -> str:
    """共有文字列・インライン文字列の本文。ふりがな（rPh）は除く。"""
    parts = [el.findtext(_S + "t") or ""]
    parts += [r.findtext(_S + "t") or "" for r in el.findall(_S + "r")]
    return "".join(parts)


def _col_index(ref: str) -> int | None:
    m = re.match(r"([A-Z]+)", ref or "")
    if not m:
        return None
    n = 0
    for ch in m.group(1):
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


# 日付を含む組み込み表示形式の ID（日本語版 Excel の和暦・年月日形式 27〜31・34〜36・50〜58 を含む）。
# 時刻だけの形式（18〜21・32・33・45〜47）は含めない（シリアル値の小数部が時刻のため、日付にすると誤る）
_BUILTIN_DATE_FORMATS = set(range(14, 18)) | {22} | set(range(27, 32)) | set(range(34, 37)) | set(range(50, 59))


def _is_date_format(code: str) -> bool:
    """表示形式のコードが日付を含むか（"..." の文字列・[...] の色や条件・\\ のエスケープを除いて判定する）。

    時刻だけの形式（h:mm など）は日付にしない。m は h・s と並ぶと「分」なので、y・d・e・g（和暦）がなく
    h か s があれば時刻とみなす。
    """
    code = re.sub(r'"[^"]*"|\[[^\]]*\]|\\.', "", code).lower()
    # 「General」「G/標準」（日本語版の標準）と指数表記（0.00E+00）の e・g は日付ではない
    code = re.sub(r"general|g/標準|e[+-]", "", code)
    if re.search(r"[ydeg]", code):
        return True
    return "m" in code and not re.search(r"[hs]", code)


def _date_styles(pkg: "_Package") -> set[int]:
    """日付の表示形式を持つセルスタイル（cellXfs の番号）の集合。"""
    if not pkg.has("xl/styles.xml"):
        return set()
    styles = pkg.xml("xl/styles.xml")
    custom = {int(f.get("numFmtId", "-1")): f.get("formatCode", "") for f in styles.iter(_S + "numFmt")}
    xfs = styles.find(_S + "cellXfs")
    result = set()
    for i, xf in enumerate(xfs.findall(_S + "xf") if xfs is not None else []):
        fmt = int(xf.get("numFmtId", "0") or 0)
        if fmt in custom:
            if _is_date_format(custom[fmt]):
                result.add(i)
        elif fmt in _BUILTIN_DATE_FORMATS:
            result.add(i)
    return result


def _serial_to_date(raw: str, date1904: bool) -> str:
    """Excel のシリアル値を YYYY-MM-DD にする。数値でなければそのまま返す。"""
    try:
        serial = float(raw)
    except ValueError:
        return raw
    base = date(1904, 1, 1) if date1904 else date(1899, 12, 30)  # 1900 年のうるう年のずれを含む基準日
    try:
        return (base + timedelta(days=int(serial))).isoformat()
    except OverflowError:
        return raw


def _cell_value(c: ET.Element, shared: list[str], date_styles: set[int], date1904: bool) -> str:
    kind = c.get("t")
    if kind == "inlineStr":
        is_ = c.find(_S + "is")
        return _string_item(is_) if is_ is not None else ""
    v = c.find(_S + "v")
    raw = v.text if v is not None and v.text is not None else ""
    if kind == "s":
        try:
            return shared[int(raw)]
        except (ValueError, IndexError):
            return ""
    if kind == "b":
        return "TRUE" if raw == "1" else "FALSE" if raw == "0" else raw
    if kind in (None, "n") and raw and int(c.get("s", "0") or 0) in date_styles:
        return _serial_to_date(raw, date1904)
    return raw


def xlsx_to_text(data: bytes) -> str:
    pkg = _Package(data, "xlsx")
    shared = []
    if pkg.has("xl/sharedStrings.xml"):
        shared = [_string_item(si) for si in pkg.xml("xl/sharedStrings.xml").iter(_S + "si")]
    rels = {r.get("Id"): r.get("Target", "") for r in pkg.xml("xl/_rels/workbook.xml.rels").iter(_PR + "Relationship")}
    workbook = pkg.xml("xl/workbook.xml")
    pr = workbook.find(_S + "workbookPr")
    date1904 = pr is not None and pr.get("date1904", "").lower() in ("1", "true")
    date_styles = _date_styles(pkg)

    sheets = list(workbook.iter(_S + "sheet"))
    if not sheets:
        raise SkillsheetError("xlsx にシートが見つかりません（「Strict Open XML」形式などは未対応です。通常の xlsx か csv で保存し直してください）")
    blocks = []
    for sheet in sheets:
        target = rels.get(sheet.get(_R + "id"), "")
        path = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
        lines = [f"# シート: {sheet.get('name', '')}"]
        for row in pkg.xml(path).iter(_S + "row"):
            cells: list[str] = []
            for c in row.iter(_S + "c"):
                if c.find(_S + "v") is None and c.find(_S + "is") is None:
                    continue  # 書式だけのセル（遠い列にあると行を無駄に埋めるため飛ばす）
                idx = _col_index(c.get("r", ""))
                if idx is None or idx < len(cells):
                    idx = len(cells)
                cells.extend([""] * (idx - len(cells)))
                cells.append(_cell_value(c, shared, date_styles, date1904).replace("\t", " ").replace("\r\n", " ").replace("\n", " "))
            line = "\t".join(cells).rstrip("\t")
            if line.strip():
                lines.append(line)
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _iter_skip_fallback(el: ET.Element):
    """el 以下の要素を順に返す。mc:Fallback（mc:Choice と同じ内容の代替表示）の中は辿らない。"""
    yield el
    for child in el:
        if child.tag != _MC_FALLBACK:
            yield from _iter_skip_fallback(child)


def _paragraph_text(p: ET.Element) -> str:
    parts = []
    for el in _iter_skip_fallback(p):
        if el.tag == _W + "t":
            parts.append(el.text or "")
        elif el.tag in (_W + "tab", _W + "br", _W + "cr"):
            parts.append(" ")
    return "".join(parts).strip()


def _table_rows(tbl: ET.Element):
    """表の行（入れ子の表の行は含めない。sdt などで包まれた行は含める）。"""
    for child in tbl:
        if child.tag == _W + "tr":
            yield child
        elif child.tag not in (_W + "tbl", _MC_FALLBACK):
            yield from _table_rows(child)


def _row_cells(tr: ET.Element):
    """行のセル（sdt・customXml などで包まれたセルを含む）。"""
    for child in tr:
        if child.tag == _W + "tc":
            yield child
        elif child.tag not in (_W + "tbl", _MC_FALLBACK, _W + "trPr", _W + "tblPrEx"):
            yield from _row_cells(child)


def _cell_text(tc: ET.Element) -> str:
    paragraphs = (el for el in _iter_skip_fallback(tc) if el.tag == _W + "p")
    return " ".join(filter(None, (_paragraph_text(p) for p in paragraphs)))


def _walk_blocks(el: ET.Element, lines: list[str]) -> None:
    """本文の段落と表を順に読む。sdt・customXml などの入れ物の中も辿る。"""
    for child in el:
        if child.tag == _W + "p":
            text = _paragraph_text(child)
            if text:
                lines.append(text)
        elif child.tag == _W + "tbl":
            for tr in _table_rows(child):
                cells = [_cell_text(tc) for tc in _row_cells(tr)]
                line = "\t".join(cells).rstrip("\t")
                if line.strip():
                    lines.append(line)
        elif child.tag != _MC_FALLBACK:
            _walk_blocks(child, lines)


def docx_to_text(data: bytes) -> str:
    pkg = _Package(data, "docx")
    body = pkg.xml("word/document.xml").find(_W + "body")
    lines: list[str] = []
    if body is not None:
        _walk_blocks(body, lines)
    return "\n".join(lines)
