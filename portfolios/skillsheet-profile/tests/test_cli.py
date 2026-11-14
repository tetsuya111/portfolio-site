import unittest

from tests.helpers import TempDirMixin, run_main


class ExtractCliTest(TempDirMixin, unittest.TestCase):
    def test_extract_prints_text(self):
        p = self.tmp / "s.txt"
        p.write_text("氏名: 山田\n", encoding="utf-8")
        code, out, err = run_main("extract", str(p))
        self.assertEqual(code, 0, err)
        self.assertIn("氏名: 山田", out)

    def test_extract_error_exit1(self):
        code, out, err = run_main("extract", str(self.tmp / "none.txt"))
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("none.txt", err)


if __name__ == "__main__":
    unittest.main()
