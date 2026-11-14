import email.message
import io
import unittest
import urllib.error
from unittest import mock

from skillsheet import fetch, readers
from skillsheet.errors import SkillsheetError
from tests.helpers import run_main

SHEET = "https://docs.google.com/spreadsheets/d/AbC-1_x/edit#gid=0"
EXPORT = "https://docs.google.com/spreadsheets/d/AbC-1_x/export?format=xlsx"


class FakeResponse:
    def __init__(self, body: bytes, content_type: str):
        self.body = io.BytesIO(body)
        self.headers = email.message.Message()
        self.headers["Content-Type"] = content_type

    def read(self, n=-1):
        return self.body.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeOpener:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.requests = response, error, []

    def __call__(self, request, timeout=None):
        self.requests.append((request, timeout))
        if self.error:
            raise self.error
        return self.response


class FetchTest(unittest.TestCase):
    def test_export_url(self):
        self.assertEqual(fetch.to_export_url(SHEET), EXPORT)

    def test_non_sheet_url_is_none(self):
        self.assertIsNone(fetch.to_export_url("https://example.com/spreadsheets/d/x"))
        self.assertIsNone(fetch.to_export_url("https://docs.google.com/document/d/x/edit"))

    def test_sheet_returns_xlsx(self):
        opener = FakeOpener(FakeResponse(b"PK..", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
        body, ext = fetch.fetch(SHEET, opener=opener)
        self.assertEqual((body, ext), (b"PK..", ".xlsx"))
        request, timeout = opener.requests[0]
        self.assertEqual(request.full_url, EXPORT)
        self.assertEqual(timeout, 30)

    def test_private_sheet_403(self):
        err = urllib.error.HTTPError(EXPORT, 403, "Forbidden", email.message.Message(), None)
        with self.assertRaises(SkillsheetError) as cm:
            fetch.fetch(SHEET, opener=FakeOpener(error=err))
        self.assertIn("非公開", str(cm.exception))
        self.assertIn("xlsx か csv", str(cm.exception))

    def test_private_sheet_html_login(self):
        opener = FakeOpener(FakeResponse(b"<html>login</html>", "text/html; charset=utf-8"))
        with self.assertRaises(SkillsheetError) as cm:
            fetch.fetch(SHEET, opener=opener)
        self.assertIn("非公開", str(cm.exception))

    def test_other_url_is_html(self):
        body, ext = fetch.fetch("https://example.com/me", opener=FakeOpener(FakeResponse(b"<p>x</p>", "text/html")))
        self.assertEqual((body, ext), (b"<p>x</p>", ".html"))

    def test_other_url_http_error(self):
        err = urllib.error.HTTPError("https://example.com/", 404, "Not Found", email.message.Message(), None)
        with self.assertRaises(SkillsheetError) as cm:
            fetch.fetch("https://example.com/", opener=FakeOpener(error=err))
        self.assertIn("404", str(cm.exception))

    def test_rejects_scheme(self):
        for url in ("file:///etc/passwd", "ftp://example.com/a.xlsx"):
            with self.assertRaises(SkillsheetError):
                fetch.fetch(url, opener=FakeOpener(FakeResponse(b"x", "text/plain")))

    def test_too_large_response(self):
        opener = FakeOpener(FakeResponse(b"x" * 20, "text/html"))
        with mock.patch.object(readers, "MAX_BYTES", 10):
            with self.assertRaises(SkillsheetError):
                fetch.fetch("https://example.com/", opener=opener)

    def test_network_error(self):
        with self.assertRaises(SkillsheetError):
            fetch.fetch("https://example.com/", opener=FakeOpener(error=urllib.error.URLError("down")))
        with self.assertRaises(SkillsheetError):
            fetch.fetch("https://example.com/", opener=FakeOpener(error=TimeoutError()))

    def test_is_url(self):
        self.assertTrue(fetch.is_url("https://x"))
        self.assertTrue(fetch.is_url("HTTP://x"))
        self.assertFalse(fetch.is_url("C:\a.xlsx"))
        self.assertFalse(fetch.is_url("file:///a"))


class ExtractUrlCliTest(unittest.TestCase):
    def test_extract_url_uses_fetch(self):
        with mock.patch("skillsheet.fetch.fetch", return_value=(b"<p>x</p>", ".html")) as f:
            code, out, err = run_main("extract", "https://example.com/me")
        self.assertEqual(code, 0, err)
        self.assertEqual(out.strip(), "x")
        f.assert_called_once_with("https://example.com/me")

    def test_extract_file_url_rejected(self):
        code, out, err = run_main("extract", "file:///etc/passwd")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
