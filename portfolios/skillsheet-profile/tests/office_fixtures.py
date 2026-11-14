"""テスト用の最小の xlsx・docx を組み立てる。"""

import io
import zipfile
from xml.sax.saxutils import escape

S = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
R = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def make_xlsx(sheets: dict[str, str], shared: list[str] | None = None, absolute_target=False,
              styles: str | None = None) -> bytes:
    """sheets はシート名 → <sheetData> の中身の XML 断片。shared は共有文字列（素のテキストか <si> の中身）。
    styles は xl/styles.xml の <styleSheet> の中身（numFmts・cellXfs）。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        if styles is not None:
            z.writestr("xl/styles.xml", f"<styleSheet {S}>{styles}</styleSheet>")
        sheet_els, rels = [], []
        for i, (name, rows) in enumerate(sheets.items(), start=1):
            sheet_els.append(f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>')
            target = f"/xl/worksheets/sheet{i}.xml" if absolute_target else f"worksheets/sheet{i}.xml"
            rels.append(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="{target}"/>')
            z.writestr(f"xl/worksheets/sheet{i}.xml", f"<worksheet {S}><sheetData>{rows}</sheetData></worksheet>")
        z.writestr("xl/workbook.xml", f"<workbook {S} {R}><sheets>{''.join(sheet_els)}</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   + "".join(rels) + "</Relationships>")
        if shared is not None:
            items = "".join(s if s.startswith("<") else f"<si><t>{escape(s)}</t></si>" for s in shared)
            z.writestr("xl/sharedStrings.xml", f"<sst {S}>{items}</sst>")
    return buf.getvalue()


def make_docx(body_xml: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", f"<w:document {W}><w:body>{body_xml}</w:body></w:document>")
    return buf.getvalue()


def para(text: str) -> str:
    return f"<w:p><w:r><w:t>{escape(text)}</w:t></w:r></w:p>"
