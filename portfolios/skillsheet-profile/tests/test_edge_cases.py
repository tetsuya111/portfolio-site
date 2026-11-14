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


class Round3Test(TempDirMixin, unittest.TestCase):
    def test_html_source_tabs(self):
        html = "<table>\n\t<tr>\n\t\t<td>a</td>\n\t\t<td>b</td>\n\t</tr>\n</table>"
        self.assertEqual(html_to_text(html), "a\tb")

    def test_html_nested_table(self):
        html = "<table><tr><td><table><tr><td>x</td></tr></table>a<br>b</td><td>c</td></tr></table>"
        self.assertTrue(html_to_text(html).endswith("a b\tc"), html_to_text(html))

    def test_japanese_general_format_is_not_date(self):
        self.assertFalse(office._is_date_format('G/標準"年"'))
        self.assertFalse(office._is_date_format("h:mm"))
        self.assertTrue(office._is_date_format("ggge年m月"))
        self.assertTrue(office._is_date_format("yyyy/m/d h:mm"))

    def test_time_builtin_is_not_date(self):
        styles = '<cellXfs count="2"><xf numFmtId="20"/><xf numFmtId="14"/></cellXfs>'
        rows = '<row r="1"><c r="A1" s="0"><v>0.395833</v></c><c r="B1" s="1"><v>43922.5</v></c></row>'
        self.assertIn("0.395833\t2020-04-01", office.xlsx_to_text(make_xlsx({"s": rows}, styles=styles)))

    def test_styled_empty_far_cell(self):
        rows = '<row r="1"><c r="A1"><v>1</v></c><c r="XFD1" s="0"/></row>'
        self.assertEqual(office.xlsx_to_text(make_xlsx({"s": rows})), "# シート: s\n1")

    def test_missing_content_type_uses_url_ext(self):
        import email.message
        from tests.test_fetch import FakeOpener

        class NoTypeResponse:
            headers = email.message.Message()

            def read(self, n=-1):
                return b"PK"

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        _, ext = fetch.fetch("https://host/sheet.xlsx", opener=FakeOpener(NoTypeResponse()))
        self.assertEqual(ext, ".xlsx")

    def test_meta_charset(self):
        from tests.test_fetch import FakeOpener, FakeResponse
        from skillsheet import readers

        body = '<meta charset="EUC-JP"><p>山田</p>'.encode("euc_jp")
        data, ext = fetch.fetch("https://host/", opener=FakeOpener(FakeResponse(body, "text/html")))
        self.assertEqual(readers.read_bytes(data, ext), "山田")

    def test_incomplete_read(self):
        import http.client
        from tests.test_fetch import FakeOpener

        with self.assertRaises(SkillsheetError):
            fetch.fetch("https://host/", opener=FakeOpener(error=http.client.IncompleteRead(b"")))

    def test_lone_surrogate_is_validation_error(self):
        errors = profile.validate(replace("name: 山田 太郎", 'name: "\\ud83d"'))
        self.assertTrue(any("name" in e for e in errors), errors)

    def test_stdin_cp932(self):
        import sys
        from unittest import mock
        from tests.helpers import run_main

        target = self.tmp / "profile.md"
        target.write_text("old", encoding="utf-8")
        fake_stdin = io.TextIOWrapper(io.BytesIO(VALID.encode("cp932")), encoding="utf-8")
        with mock.patch.object(sys, "stdin", fake_stdin):
            code, out, err = run_main("apply", "-", "--target", str(target))
        self.assertEqual(code, 0, err)


if __name__ == "__main__":
    unittest.main()
