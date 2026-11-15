import io
import unittest
import zipfile
from unittest import mock

from skillsheet import office, readers
from skillsheet.errors import SkillsheetError
from tests.office_fixtures import make_docx, make_xlsx, para


class XlsxTest(unittest.TestCase):
    def test_shared_strings_and_sheet_names(self):
        data = make_xlsx(
            {"経歴": '<row r="1"><c r="A1" t="s"><v>0</v></c></row>',
             "スキル": '<row r="1"><c r="A1" t="s"><v>1</v></c></row>'},
            shared=["2020年 Web開発", "Python"],
        )
        text = office.xlsx_to_text(data)
        self.assertLess(text.index("# シート: 経歴"), text.index("# シート: スキル"))
        self.assertIn("2020年 Web開発", text)
        self.assertIn("Python", text)

    def test_numbers_and_gaps(self):
        data = make_xlsx({"s": '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="C1"><v>2020</v></c></row>'},
                         shared=["年"])
        self.assertIn("年\t\t2020", office.xlsx_to_text(data))

    def test_inline_bool_and_rich_text(self):
        data = make_xlsx(
            {"s": '<row r="1"><c r="A1" t="s"><v>0</v></c>'
                  '<c r="B1" t="inlineStr"><is><t>AWS</t></is></c>'
                  '<c r="C1" t="b"><v>1</v></c><c r="D1" t="str"><v>式</v></c></row>'},
            shared=["<si><r><t>Py</t></r><r><t>thon</t></r></si>"],
        )
        self.assertIn("Python\tAWS\tTRUE\t式", office.xlsx_to_text(data))

    def test_skips_phonetic_reading(self):
        data = make_xlsx(
            {"s": '<row r="1"><c r="A1" t="s"><v>0</v></c>'
                  '<c r="B1" t="inlineStr"><is><t>東京</t><rPh sb="0" eb="2"><t>トウキョウ</t></rPh></is></c></row>'},
            shared=['<si><t>山田太郎</t><rPh sb="0" eb="2"><t>ヤマダ</t></rPh><phoneticPr fontId="1"/></si>'],
        )
        self.assertIn("山田太郎\t東京", office.xlsx_to_text(data))
        self.assertNotIn("ヤマダ", office.xlsx_to_text(data))

    def test_cells_without_ref(self):
        data = make_xlsx({"s": '<row><c t="inlineStr"><is><t>a</t></is></c><c t="inlineStr"><is><t>b</t></is></c></row>'})
        self.assertIn("a\tb", office.xlsx_to_text(data))

    def test_skips_empty_rows(self):
        data = make_xlsx({"s": '<row r="1"><c r="A1"/></row><row r="2"><c r="A2"><v>5</v></c></row>'})
        self.assertEqual(office.xlsx_to_text(data), "# シート: s\n5")

    def test_absolute_target(self):
        data = make_xlsx({"s": '<row r="1"><c r="A1"><v>7</v></c></row>'}, absolute_target=True)
        self.assertIn("7", office.xlsx_to_text(data))

    def test_read_bytes_xlsm(self):
        data = make_xlsx({"s": '<row r="1"><c r="A1"><v>7</v></c></row>'})
        self.assertIn("7", readers.read_bytes(data, ".xlsm"))


class DocxTest(unittest.TestCase):
    def test_docx_paragraphs_and_table(self):
        table = ("<w:tbl><w:tr><w:tc>" + para("言語") + "</w:tc><w:tc>" + para("Python") + "</w:tc></w:tr></w:tbl>")
        text = office.docx_to_text(make_docx(para("自己PR") + "<w:p/>" + table))
        self.assertEqual(text, "自己PR\n言語\tPython")

    def test_docx_content_controls(self):
        body = ("<w:sdt><w:sdtContent>" + para("氏名 T.Y") + "<w:tbl><w:tr><w:tc>" + para("言語")
                + "</w:tc><w:tc>" + para("Go") + "</w:tc></w:tr></w:tbl></w:sdtContent></w:sdt>"
                + "<w:customXml>" + para("自己PR") + "</w:customXml>")
        self.assertEqual(office.docx_to_text(make_docx(body)), "氏名 T.Y\n言語\tGo\n自己PR")

    def test_docx_alternate_content_once(self):
        mc = 'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"'
        p = ('<w:p><w:r><mc:AlternateContent ' + mc + '><mc:Choice Requires="wps"><w:txbxContent>' + para("枠内")
             + '</w:txbxContent></mc:Choice><mc:Fallback><w:txbxContent>' + para("枠内")
             + "</w:txbxContent></mc:Fallback></mc:AlternateContent></w:r></w:p>")
        self.assertEqual(office.docx_to_text(make_docx(p)), "枠内")

    def test_read_bytes_docx(self):
        self.assertEqual(readers.read_bytes(make_docx(para("x")), ".docx"), "x")


class BrokenTest(unittest.TestCase):
    def test_broken_zip(self):
        with self.assertRaises(SkillsheetError):
            office.xlsx_to_text(b"not zip")
        with self.assertRaises(SkillsheetError):
            office.docx_to_text(b"not zip")

    def test_missing_part(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("x.txt", "x")
        with self.assertRaises(SkillsheetError):
            office.xlsx_to_text(buf.getvalue())

    def test_broken_xml(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("word/document.xml", "<w:document")
        with self.assertRaises(SkillsheetError):
            office.docx_to_text(buf.getvalue())

    def test_uncompressed_limit(self):
        data = make_docx(para("x" * 1000))
        with mock.patch.object(readers, "MAX_BYTES", 500):
            with self.assertRaises(SkillsheetError):
                office.docx_to_text(data)


if __name__ == "__main__":
    unittest.main()
