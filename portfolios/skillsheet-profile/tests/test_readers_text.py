import unittest
from unittest import mock

from skillsheet import readers
from skillsheet.errors import SkillsheetError
from tests.helpers import TempDirMixin


class TextReaderTest(TempDirMixin, unittest.TestCase):
    def test_utf8_bom_text(self):
        p = self.tmp / "a.txt"
        p.write_bytes("﻿氏名\t山田".encode("utf-8"))
        self.assertEqual(readers.read_file(p), "氏名\t山田")

    def test_cp932_csv(self):
        p = self.tmp / "a.csv"
        p.write_bytes("氏名,山田\n".encode("cp932"))
        self.assertEqual(readers.read_file(p), "氏名,山田\n")

    def test_uppercase_ext(self):
        p = self.tmp / "A.MD"
        p.write_text("# x", encoding="utf-8")
        self.assertEqual(readers.read_file(p), "# x")

    def test_unsupported_ext(self):
        p = self.tmp / "a.xls"
        p.write_bytes(b"x")
        with self.assertRaises(SkillsheetError) as cm:
            readers.read_file(p)
        self.assertIn(".xls", str(cm.exception))
        self.assertIn("xlsx か csv", str(cm.exception))

    def test_missing_file(self):
        with self.assertRaises(SkillsheetError):
            readers.read_file(self.tmp / "none.txt")

    def test_directory(self):
        d = self.tmp / "dir.txt"
        d.mkdir()
        with self.assertRaises(SkillsheetError):
            readers.read_file(d)

    def test_too_large(self):
        p = self.tmp / "a.txt"
        p.write_bytes(b"x" * 11)
        with mock.patch.object(readers, "MAX_BYTES", 10):
            with self.assertRaises(SkillsheetError):
                readers.read_file(p)

    def test_undecodable(self):
        with self.assertRaises(SkillsheetError):
            readers.read_bytes(b"\x81\x00\xff\xfe\x80", ".txt")


if __name__ == "__main__":
    unittest.main()
