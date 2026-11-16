import unittest

from stackgen import StackError
from stackgen.config import Config, load_config
from tests.helpers import TempDirMixin, write, write_json


class LoadConfigTest(TempDirMixin, unittest.TestCase):
    def test_reads_valid_config(self):
        p = write_json(self.tmp / "config.json", {"domain": "API.portfolio.link", "https": False})
        self.assertEqual(load_config(p), Config("api.portfolio.link", False))

    def test_https_defaults_to_true(self):
        p = write_json(self.tmp / "config.json", {"domain": "api.portfolio.link"})
        self.assertTrue(load_config(p).https)

    def test_rejects_invalid(self):
        cases = {
            "missing": None,
            "bad json": "{",
            "space": {"domain": "a b"},
            "url": {"domain": "https://x.com"},
            "single label": {"domain": "localhost"},
            "example": {"domain": "api.example.com"},
            "https string": {"domain": "api.portfolio.link", "https": "true"},
            "not object": [],
        }
        for name, data in cases.items():
            with self.subTest(name):
                p = self.tmp / f"{name}.json"
                if isinstance(data, str):
                    write(p, data)
                elif data is not None:
                    write_json(p, data)
                with self.assertRaises(StackError):
                    load_config(p)
