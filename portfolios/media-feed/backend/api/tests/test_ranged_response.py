from django.test import SimpleTestCase

from api.ranged_response import (
    RangeNotSatisfiable,
    is_not_modified,
    make_etag,
    parse_range_header,
)


class _FakeRequest:
    def __init__(self, **headers):
        self.META = headers


class ParseRangeHeaderTest(SimpleTestCase):
    TOTAL = 1000

    def test_no_header_returns_none(self):
        self.assertIsNone(parse_range_header(None, self.TOTAL))
        self.assertIsNone(parse_range_header('', self.TOTAL))

    def test_explicit_range(self):
        self.assertEqual(parse_range_header('bytes=0-499', self.TOTAL), (0, 499))
        self.assertEqual(parse_range_header('bytes=500-999', self.TOTAL), (500, 999))

    def test_open_ended_range(self):
        self.assertEqual(parse_range_header('bytes=500-', self.TOTAL), (500, 999))
        self.assertEqual(parse_range_header('bytes=0-', self.TOTAL), (0, 999))

    def test_suffix_range_returns_tail(self):
        self.assertEqual(parse_range_header('bytes=-100', self.TOTAL), (900, 999))

    def test_suffix_larger_than_file_clamps_to_whole_file(self):
        self.assertEqual(parse_range_header('bytes=-5000', self.TOTAL), (0, 999))

    def test_end_beyond_eof_is_clamped(self):
        self.assertEqual(parse_range_header('bytes=900-5000', self.TOTAL), (900, 999))

    def test_single_byte_probe(self):
        # Safari が再生前に投げる探りのリクエスト。
        self.assertEqual(parse_range_header('bytes=0-1', self.TOTAL), (0, 1))

    def test_start_beyond_eof_is_not_satisfiable(self):
        with self.assertRaises(RangeNotSatisfiable):
            parse_range_header('bytes=1000-', self.TOTAL)
        with self.assertRaises(RangeNotSatisfiable):
            parse_range_header('bytes=5000-6000', self.TOTAL)

    def test_zero_length_suffix_is_not_satisfiable(self):
        with self.assertRaises(RangeNotSatisfiable):
            parse_range_header('bytes=-0', self.TOTAL)

    def test_empty_file_is_not_satisfiable(self):
        with self.assertRaises(RangeNotSatisfiable):
            parse_range_header('bytes=0-10', 0)

    def test_malformed_headers_are_ignored(self):
        # RFC 9110: 構文が不正な Range は無視して 200 を返す（416 ではない）。
        for header in ('bytes=abc-def', 'items=0-10', 'bytes=', 'bytes=-', 'garbage'):
            with self.subTest(header=header):
                self.assertIsNone(parse_range_header(header, self.TOTAL))

    def test_reversed_range_is_ignored(self):
        self.assertIsNone(parse_range_header('bytes=500-100', self.TOTAL))

    def test_multiple_ranges_uses_first(self):
        self.assertEqual(parse_range_header('bytes=0-99,200-299', self.TOTAL), (0, 99))


class ConditionalGetTest(SimpleTestCase):
    ETAG = '"abc-def"'
    MTIME = 1_700_000_000.0

    def test_matching_etag_is_not_modified(self):
        req = _FakeRequest(HTTP_IF_NONE_MATCH=self.ETAG)
        self.assertTrue(is_not_modified(req, self.ETAG, self.MTIME))

    def test_non_matching_etag_is_modified(self):
        req = _FakeRequest(HTTP_IF_NONE_MATCH='"other"')
        self.assertFalse(is_not_modified(req, self.ETAG, self.MTIME))

    def test_star_matches(self):
        req = _FakeRequest(HTTP_IF_NONE_MATCH='*')
        self.assertTrue(is_not_modified(req, self.ETAG, self.MTIME))

    def test_weak_comparison(self):
        req = _FakeRequest(HTTP_IF_NONE_MATCH='W/"abc-def"')
        self.assertTrue(is_not_modified(req, self.ETAG, self.MTIME))

    def test_if_modified_since_not_modified(self):
        req = _FakeRequest(HTTP_IF_MODIFIED_SINCE='Wed, 15 Nov 2023 00:00:00 GMT')
        # ファイルの mtime がヘッダより古ければ 304。
        self.assertTrue(is_not_modified(req, None, 1_690_000_000.0))

    def test_if_modified_since_modified(self):
        req = _FakeRequest(HTTP_IF_MODIFIED_SINCE='Wed, 15 Nov 2023 00:00:00 GMT')
        self.assertFalse(is_not_modified(req, None, 1_800_000_000.0))

    def test_etag_takes_precedence_over_date(self):
        # If-None-Match が一致しなければ、日付が古くても 304 にしない。
        req = _FakeRequest(
            HTTP_IF_NONE_MATCH='"other"',
            HTTP_IF_MODIFIED_SINCE='Wed, 15 Nov 2023 00:00:00 GMT',
        )
        self.assertFalse(is_not_modified(req, self.ETAG, 1_690_000_000.0))

    def test_no_conditional_headers(self):
        self.assertFalse(is_not_modified(_FakeRequest(), self.ETAG, self.MTIME))

    def test_make_etag_changes_with_content(self):
        self.assertNotEqual(make_etag(100, self.MTIME), make_etag(101, self.MTIME))
        self.assertNotEqual(make_etag(100, self.MTIME), make_etag(100, self.MTIME + 1))
