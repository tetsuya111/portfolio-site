"""xlsx・docx（Office Open XML）を標準ライブラリだけでテキストにする。"""

import io
import posixpath
import re
import zipfile
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
        except ET.ParseError:
            raise SkillsheetError(f"{self.kind} の {name} を読めません（壊れています）") from None


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


def _cell_value(c: ET.Element, shared: list[str]) -> str:
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
    return raw


def xlsx_to_text(data: bytes) -> str:
    pkg = _Package(data, "xlsx")
    shared = []
    if pkg.has("xl/sharedStrings.xml"):
        shared = [_string_item(si) for si in pkg.xml("xl/sharedStrings.xml").iter(_S + "si")]
    rels = {r.get("Id"): r.get("Target", "") for r in pkg.xml("xl/_rels/workbook.xml.rels").iter(_PR + "Relationship")}

    blocks = []
    for sheet in pkg.xml("xl/workbook.xml").iter(_S + "sheet"):
        target = rels.get(sheet.get(_R + "id"), "")
        path = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
        lines = [f"# シート: {sheet.get('name', '')}"]
        for row in pkg.xml(path).iter(_S + "row"):
            cells: list[str] = []
            for c in row.iter(_S + "c"):
                idx = _col_index(c.get("r", ""))
                if idx is None or idx < len(cells):
                    idx = len(cells)
                cells.extend([""] * (idx - len(cells)))
                cells.append(_cell_value(c, shared).replace("\t", " ").replace("\r\n", " ").replace("\n", " "))
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
                cells = [_cell_text(tc) for tc in tr if tc.tag == _W + "tc"]
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
