"""レビューで見つかった境界条件のテスト。"""

import io
import os
import stat
import unittest
import zipfile

from skillsheet import fetch, office, profile
from skillsheet.errors import SkillsheetError
from skillsheet.html_text import html_to_text
from tests.helpers import TempDirMixin
from tests.office_fixtures import W, make_docx, make_xlsx, para
from tests.test_profile import VALID, replace


class HtmlCellTest(unittest.TestCase):
    def test_block_inside_cell_keeps_columns(self):
        self.assertEqual(html_to_text("<table><tr><td>a<br>b</td><td>c</td></tr></table>"), "a b\tc")
        self.assertEqual(html_to_text("<table><tr><td><p>x</p><div>y</div></td><td>z</td></tr></table>"), "x y\tz")

    def test_rows_still_split(self):
        self.assertEqual(html_to_text("<table><tr><td>a</td><td>b</td></tr><tr><td>c</td></tr></table>"), "a\tb\nc")


class XlsxEdgeTest(unittest.TestCase):
    STYLES = ('<numFmts count="1"><numFmt numFmtId="176" formatCode="yyyy/mm"/></numFmts>'
              '<cellXfs count="4"><xf numFmtId="0"/><xf numFmtId="14"/><xf numFmtId="176"/>'
              '<xf numFmtId="177"/></cellXfs>')

    def test_date_cells(self):
        rows = ('<row r="1"><c r="A1" s="1"><v>43922</v></c><c r="B1" s="2"><v>44287</v></c>'
                '<c r="C1" s="0"><v>43922</v></c><c r="D1"><v>3.5</v></c></row>')
        text = office.xlsx_to_text(make_xlsx({"s": rows}, styles=self.STYLES))
        self.assertIn("2020-04-01\t2021-04-01\t43922\t3.5", text)

    def test_non_date_custom_format(self):
        styles = ('<numFmts count="1"><numFmt numFmtId="177" formatCode="&quot;y&quot;0.00"/></numFmts>'
                  '<cellXfs count="1"><xf numFmtId="177"/></cellXfs>')
        text = office.xlsx_to_text(make_xlsx({"s": '<row r="1"><c r="A1" s="0"><v>12</v></c></row>'}, styles=styles))
        self.assertIn("12", text)

    def test_no_sheets_is_error(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("xl/workbook.xml", '<workbook xmlns="http://purl.oclc.org/ooxml/spreadsheetml/main"/>')
            z.writestr("xl/_rels/workbook.xml.rels",
                       '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
        with self.assertRaises(SkillsheetError) as cm:
            office.xlsx_to_text(buf.getvalue())
        self.assertIn("シート", str(cm.exception))

    def test_corrupt_member(self):
        data = bytearray(make_docx(para("x" * 200)))
        # 中身（圧縮なしのデータ部分）を壊して CRC を合わなくする
        i = data.index(b"xxxx")
        data[i:i + 4] = b"yyyy"
        with self.assertRaises(SkillsheetError):
            office.docx_to_text(bytes(data))


class DocxEdgeTest(unittest.TestCase):
    def test_cell_inside_content_control(self):
        row = ("<w:tbl><w:tr><w:tc>" + para("言語") + "</w:tc><w:sdt><w:sdtContent><w:tc>" + para("Go")
               + "</w:tc></w:sdtContent></w:sdt></w:tr></w:tbl>")
        self.assertEqual(office.docx_to_text(make_docx(row)), "言語\tGo")

    def test_namespace_constant(self):
        self.assertIn("wordprocessingml", W)


class SheetUrlTest(unittest.TestCase):
    def test_published_url(self):
        self.assertEqual(
            fetch.to_export_url("https://docs.google.com/spreadsheets/d/e/2PACX-1vabc/pubhtml"),
            "https://docs.google.com/spreadsheets/d/e/2PACX-1vabc/pub?output=xlsx",
        )

    def test_case_and_http(self):
        self.assertEqual(
            fetch.to_export_url("HTTP://Docs.Google.com/spreadsheets/d/AbC/edit"),
            "https://docs.google.com/spreadsheets/d/AbC/export?format=xlsx",
        )


class ProfileEdgeTest(TempDirMixin, unittest.TestCase):
    def test_empty_links_followed_by_key(self):
        text = replace("links:\n  - label: GitHub\n    url: https://github.com/\n", "links:\nextra: x\n")
        errors = profile.validate(text)
        self.assertTrue(any(e.startswith("links") for e in errors), errors)

    def test_tab_before_hash(self):
        errors = profile.validate(replace("role: フリーランス Web エンジニア", "role: Engineer\t#1"))
        self.assertTrue(any("role" in e for e in errors), errors)

    @unittest.skipIf(os.name == "nt", "POSIX のパーミッションのみ")
    def test_keeps_mode(self):
        target = self.tmp / "profile.md"
        target.write_text("old", encoding="utf-8")
        os.chmod(target, 0o644)
        profile.write_profile(VALID, target)
        self.assertEqual(stat.S_IMODE(os.stat(target).st_mode), 0o644)


if __name__ == "__main__":
    unittest.main()
