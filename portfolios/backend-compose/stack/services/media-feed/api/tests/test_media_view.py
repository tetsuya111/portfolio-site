import shutil
import tempfile
from pathlib import Path

from django.test import TestCase, override_settings
from django.urls import reverse

from api.models import Content

MEDIA_BYTES = bytes(range(256)) * 8  # 2048 バイト


class ContentMediaViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = Path(tempfile.mkdtemp())
        (cls.media_root / 'videos').mkdir()
        (cls.media_root / 'videos' / 'sample.mp4').write_bytes(MEDIA_BYTES)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.content = Content.objects.create(
            id='test-content-id',
            type=Content.TYPE_VIDEO,
            title='テスト動画',
            path='videos/sample.mp4',
        )
        self.url = reverse('content_media', args=[self.content.id])

    def _get(self, **headers):
        with override_settings(MEDIA_ROOT=self.media_root, MEDIA_CACHE_MAX_AGE=2592000):
            return self.client.get(self.url, **headers)

    def _body(self, response):
        return b''.join(response.streaming_content)

    def test_full_request_returns_200_with_accept_ranges(self):
        res = self._get()
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Accept-Ranges'], 'bytes')
        self.assertEqual(res['Content-Length'], str(len(MEDIA_BYTES)))
        self.assertEqual(self._body(res), MEDIA_BYTES)

    def test_full_request_sets_cache_headers(self):
        res = self._get()
        self.assertIn('max-age=2592000', res['Cache-Control'])
        self.assertIn('immutable', res['Cache-Control'])
        self.assertTrue(res['ETag'])
        self.assertTrue(res['Last-Modified'])

    def test_range_request_returns_206(self):
        res = self._get(HTTP_RANGE='bytes=0-99')
        self.assertEqual(res.status_code, 206)
        self.assertEqual(res['Content-Range'], f'bytes 0-99/{len(MEDIA_BYTES)}')
        self.assertEqual(res['Content-Length'], '100')
        self.assertEqual(self._body(res), MEDIA_BYTES[:100])

    def test_range_request_from_middle(self):
        res = self._get(HTTP_RANGE='bytes=1000-1099')
        self.assertEqual(res.status_code, 206)
        self.assertEqual(self._body(res), MEDIA_BYTES[1000:1100])

    def test_open_ended_range_reaches_eof(self):
        res = self._get(HTTP_RANGE='bytes=2000-')
        self.assertEqual(res.status_code, 206)
        self.assertEqual(
            res['Content-Range'], f'bytes 2000-{len(MEDIA_BYTES) - 1}/{len(MEDIA_BYTES)}'
        )
        self.assertEqual(self._body(res), MEDIA_BYTES[2000:])

    def test_suffix_range_returns_tail(self):
        res = self._get(HTTP_RANGE='bytes=-48')
        self.assertEqual(res.status_code, 206)
        self.assertEqual(self._body(res), MEDIA_BYTES[-48:])

    def test_unsatisfiable_range_returns_416(self):
        res = self._get(HTTP_RANGE='bytes=99999-')
        self.assertEqual(res.status_code, 416)
        self.assertEqual(res['Content-Range'], f'bytes */{len(MEDIA_BYTES)}')

    def test_malformed_range_falls_back_to_200(self):
        res = self._get(HTTP_RANGE='bytes=abc-def')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self._body(res), MEDIA_BYTES)

    def test_conditional_get_returns_304(self):
        first = self._get()
        etag = first['ETag']
        self._body(first)  # ストリームを閉じる

        second = self._get(HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(second.status_code, 304)
        self.assertEqual(second.content, b'')

    def test_missing_content_returns_404(self):
        res = self.client.get(reverse('content_media', args=['does-not-exist']))
        self.assertEqual(res.status_code, 404)

    def test_missing_file_returns_404(self):
        Content.objects.create(
            id='missing-file', type=Content.TYPE_VIDEO, path='videos/nope.mp4'
        )
        with override_settings(MEDIA_ROOT=self.media_root):
            res = self.client.get(reverse('content_media', args=['missing-file']))
        self.assertEqual(res.status_code, 404)
