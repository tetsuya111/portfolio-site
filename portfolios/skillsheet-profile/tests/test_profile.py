import io
import json
import unittest
from unittest import mock

from skillsheet import profile
from tests.helpers import TempDirMixin, run_main

VALID = """---
name: 山田 太郎
role: フリーランス Web エンジニア
summary: Web アプリケーションの設計から AWS 上での運用までを一人で担当します。
links:
  - label: GitHub
    url: https://github.com/
---

## 自己紹介

（ここに自己紹介を書く。）

## 経歴

- 2020年〜2024年: 事業会社で Web サービスの開発に従事
- 2024年〜: フリーランスとして独立

## スキル

- TypeScript / React / Astro
"""


def replace(old, new):
    assert old in VALID
    return VALID.replace(old, new)


class ValidateTest(unittest.TestCase):
    def test_valid_sample(self):
        self.assertEqual(profile.validate(VALID), [])

    def test_valid_without_optional(self):
        text = replace("summary: Web アプリケーションの設計から AWS 上での運用までを一人で担当します。\n", "")
        text = text.replace("links:\n  - label: GitHub\n    url: https://github.com/\n", "links: []\n")
        self.assertEqual(profile.validate(text), [])

    def test_bom_and_crlf(self):
        self.assertEqual(profile.validate("﻿" + VALID.replace("\n", "\r\n")), [])

    def test_quoted_value_with_colon(self):
        self.assertEqual(profile.validate(replace("role: フリーランス Web エンジニア", 'role: "PM: 兼 エンジニア"')), [])
        self.assertEqual(profile.validate(replace("role: フリーランス Web エンジニア", "role: 'PM: it''s'")), [])

    def test_unquoted_colon_is_error(self):
        errors = profile.validate(replace("role: フリーランス Web エンジニア", "role: PM: 兼 エンジニア"))
        self.assertTrue(any("role" in e and "クォート" in e for e in errors), errors)

    def test_non_string_scalar_is_error(self):
        errors = profile.validate(replace("name: 山田 太郎", "name: 2020"))
        self.assertTrue(any("name" in e for e in errors), errors)

    def test_missing_name(self):
        errors = profile.validate(replace("name: 山田 太郎\n", ""))
        self.assertTrue(any("name" in e for e in errors), errors)

    def test_empty_role(self):
        errors = profile.validate(replace("role: フリーランス Web エンジニア", 'role: ""'))
        self.assertTrue(any("role" in e for e in errors), errors)

    def test_bad_link_url(self):
        errors = profile.validate(replace("url: https://github.com/", "url: javascript:alert(1)"))
        self.assertTrue(any("links" in e and "url" in e for e in errors), errors)

    def test_link_without_label(self):
        errors = profile.validate(replace("  - label: GitHub\n    url:", "  - url:"))
        self.assertTrue(any("links" in e and "label" in e for e in errors), errors)

    def test_missing_heading(self):
        errors = profile.validate(replace("## 経歴\n", ""))
        self.assertTrue(any("## 経歴" in e for e in errors), errors)

    def test_no_frontmatter(self):
        self.assertTrue(profile.validate("## 自己紹介\n"))
        self.assertTrue(profile.validate("---\nname: a\nrole: b\n"))  # 閉じの --- なし

    def test_unparsable_line(self):
        errors = profile.validate(replace("role: フリーランス Web エンジニア", "role: x\n  nested: y"))
        self.assertTrue(any("行目" in e for e in errors), errors)

    def test_bare_links_is_error(self):
        errors = profile.validate(replace("links:\n  - label: GitHub\n    url: https://github.com/\n", "links:\n"))
        self.assertTrue(any("links" in e for e in errors), errors)

    def test_zero_indent_items(self):
        text = replace("  - label: GitHub\n    url: https://github.com/", "- label: GitHub\n  url: https://github.com/")
        self.assertEqual(profile.validate(text), [])

    def test_misaligned_continuation(self):
        for bad in ("      url: https://github.com/", "  url: https://github.com/"):
            errors = profile.validate(replace("    url: https://github.com/", bad))
            self.assertTrue(any("インデント" in e or "links" in e for e in errors), (bad, errors))

    def test_misaligned_items(self):
        text = replace("    url: https://github.com/\n", "    url: https://github.com/\n    - label: X\n      url: https://x.com/\n")
        self.assertTrue(profile.validate(text))

    def test_more_non_string_scalars(self):
        for value in ("2024-4-1", "0b101", "1_000", "yes", "12:30"):
            errors = profile.validate(replace("role: フリーランス Web エンジニア", f"role: {value}"))
            self.assertTrue(any("role" in e for e in errors), (value, errors))

    def test_url_rules(self):
        for bad in ("https://[github", "https://exa%zzmple.com", "https://", "https://a b.com", "mailto:a@b.c"):
            errors = profile.validate(replace("url: https://github.com/", f'url: "{bad}"'))
            self.assertTrue(any("url" in e for e in errors), (bad, errors))
        for good in ("HTTPS://github.com/x", "http://localhost:4321/", "https://例え.jp/"):
            self.assertEqual(profile.validate(replace("url: https://github.com/", f"url: {good}")), [], good)

    def test_duplicate_key(self):
        errors = profile.validate(replace("role: フリーランス Web エンジニア", "role: a\nrole: b"))
        self.assertTrue(any("role" in e for e in errors), errors)


class WriteTest(TempDirMixin, unittest.TestCase):
    def test_write_replaces_atomically(self):
        target = self.tmp / "profile.md"
        target.write_text("old", encoding="utf-8")
        profile.write_profile(VALID.replace("\n", "\r\n"), target)
        self.assertEqual(target.read_bytes(), VALID.encode("utf-8"))
        self.assertEqual([p.name for p in self.tmp.iterdir()], ["profile.md"])

    def test_adds_trailing_newline_and_strips_bom(self):
        target = self.tmp / "profile.md"
        profile.write_profile("﻿" + VALID.rstrip("\n"), target)
        self.assertEqual(target.read_bytes(), VALID.encode("utf-8"))

    def test_default_target_exists(self):
        self.assertTrue(profile.DEFAULT_TARGET.is_file(), profile.DEFAULT_TARGET)
        self.assertEqual(profile.DEFAULT_TARGET.parts[-4:], ("src", "content", "profile", "profile.md"))


class ApplyCliTest(TempDirMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.target = self.tmp / "profile.md"
        self.target.write_bytes("元の内容\n".encode("utf-8"))

    def test_apply_stdin(self):
        with mock.patch("sys.stdin", io.StringIO(VALID)):
            code, out, err = run_main("apply", "-", "--target", str(self.target))
        self.assertEqual(code, 0, err)
        result = json.loads(out)
        self.assertTrue(result["replaced"])
        self.assertEqual(result["target"], str(self.target))
        self.assertEqual(self.target.read_text(encoding="utf-8"), VALID)

    def test_apply_file(self):
        draft = self.tmp / "draft.md"
        draft.write_bytes(("﻿" + VALID).encode("utf-8"))
        code, out, err = run_main("apply", str(draft), "--target", str(self.target))
        self.assertEqual(code, 0, err)
        self.assertEqual(self.target.read_text(encoding="utf-8"), VALID)

    def test_invalid_keeps_target(self):
        before = self.target.read_bytes()
        with mock.patch("sys.stdin", io.StringIO(replace("name: 山田 太郎\n", ""))):
            code, out, err = run_main("apply", "-", "--target", str(self.target))
        self.assertEqual(code, 1)
        self.assertIn("name", err)
        self.assertEqual(self.target.read_bytes(), before)

    def test_apply_cp932_draft(self):
        draft = self.tmp / "draft.md"
        draft.write_bytes(VALID.encode("cp932"))
        code, out, err = run_main("apply", str(draft), "--target", str(self.target))
        self.assertEqual(code, 0, err)
        # cp932 の往復で「〜」は全角チルダになる（cp932 の仕様）
        self.assertEqual(self.target.read_text(encoding="utf-8"), VALID.encode("cp932").decode("cp932"))

    def test_apply_draft_is_directory(self):
        code, out, err = run_main("apply", str(self.tmp), "--target", str(self.target))
        self.assertEqual(code, 1)

    def test_missing_draft(self):
        code, out, err = run_main("apply", str(self.tmp / "none.md"), "--target", str(self.target))
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
