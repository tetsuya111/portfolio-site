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


def _text_of(el: ET.Element, tag: str) -> str:
    return "".join(t.text or "" for t in el.iter(tag))


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
        return _text_of(c, _S + "t")
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
        shared = [_text_of(si, _S + "t") for si in pkg.xml("xl/sharedStrings.xml").iter(_S + "si")]
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


def _paragraph_text(p: ET.Element) -> str:
    parts = []
    for el in p.iter():
        if el.tag == _W + "t":
            parts.append(el.text or "")
        elif el.tag == _W + "tab":
            parts.append(" ")
        elif el.tag in (_W + "br", _W + "cr"):
            parts.append(" ")
    return "".join(parts).strip()


def docx_to_text(data: bytes) -> str:
    pkg = _Package(data, "docx")
    body = pkg.xml("word/document.xml").find(_W + "body")
    lines = []
    for child in body if body is not None else []:
        if child.tag == _W + "p":
            text = _paragraph_text(child)
            if text:
                lines.append(text)
        elif child.tag == _W + "tbl":
            for tr in child.iter(_W + "tr"):
                cells = [" ".join(filter(None, (_paragraph_text(p) for p in tc.iter(_W + "p")))) for tc in tr.findall(_W + "tc")]
                line = "\t".join(cells).rstrip("\t")
                if line.strip():
                    lines.append(line)
    return "\n".join(lines)
