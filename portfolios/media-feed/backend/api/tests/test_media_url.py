import os
from unittest import mock

from django.test import SimpleTestCase, TestCase

from api import media_url
from api.models import Content
from api.serializers import ContentSerializer


def _clear_caches():
    media_url._s3_presigned_url_cached.cache_clear()
    media_url._cloudfront_signer.cache_clear()


class _Stub:
    """Content の最低限の代替。DBを触らずに解決だけを確かめる。"""

    def __init__(self, path, type='video', id='abc', media_version=0):
        self.path = path
        self.type = type
        self.id = id
        self.media_version = media_version


class DeliveryModeTest(SimpleTestCase):
    def test_default_is_proxy(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('MEDIA_DELIVERY_MODE', None)
            self.assertEqual(media_url.delivery_mode(), media_url.MODE_PROXY)

    def test_unknown_mode_falls_back_to_proxy(self):
        with mock.patch.dict(os.environ, {'MEDIA_DELIVERY_MODE': 'nonsense'}):
            self.assertEqual(media_url.delivery_mode(), media_url.MODE_PROXY)

    def test_known_modes(self):
        for mode in ('cdn', 's3', 'proxy'):
            with mock.patch.dict(os.environ, {'MEDIA_DELIVERY_MODE': mode.upper()}):
                self.assertEqual(media_url.delivery_mode(), mode)


class ExpiryQuantizationTest(SimpleTestCase):
    def test_same_window_yields_same_expiry(self):
        # 同じ1時間の中では有効期限が変わらない → URLが変わらない → ブラウザキャッシュが効く。
        base = 1_700_000_000.0
        self.assertEqual(
            media_url.quantized_expires_at(base),
            media_url.quantized_expires_at(base + 1800),
        )

    def test_next_window_yields_different_expiry(self):
        base = 1_700_000_000.0
        self.assertNotEqual(
            media_url.quantized_expires_at(base),
            media_url.quantized_expires_at(base + 3600),
        )

    def test_expiry_is_in_the_future(self):
        base = 1_700_000_000.0
        self.assertGreater(media_url.quantized_expires_at(base), base)


class ResolveMediaUrlTest(SimpleTestCase):
    def setUp(self):
        _clear_caches()

    def test_empty_path_returns_none(self):
        self.assertIsNone(media_url.resolve_media_url(_Stub('')))

    def test_absolute_url_is_returned_as_is(self):
        url = 'https://example.com/a.mp4'
        self.assertEqual(media_url.resolve_media_url(_Stub(url)), url)

    def test_local_path_returns_none(self):
        # ローカルファイルはアプリ経由でしか返せない。
        with mock.patch.dict(os.environ, {'MEDIA_DELIVERY_MODE': 's3'}):
            self.assertIsNone(media_url.resolve_media_url(_Stub('videos/a.mp4')))

    def test_proxy_mode_returns_none_for_s3_path(self):
        with mock.patch.dict(os.environ, {'MEDIA_DELIVERY_MODE': 'proxy'}):
            self.assertIsNone(media_url.resolve_media_url(_Stub('s3://b/media/videos/a.mp4')))

    def test_s3_mode_generates_presigned_url(self):
        client = mock.Mock()
        client.generate_presigned_url.return_value = 'https://signed.example/a.mp4'
        with mock.patch.dict(os.environ, {'MEDIA_DELIVERY_MODE': 's3'}), \
                mock.patch.object(media_url, 'get_s3_client', return_value=client):
            url = media_url.resolve_media_url(_Stub('s3://b/media/videos/a.mp4'))
        self.assertEqual(url, 'https://signed.example/a.mp4')

    def test_s3_mode_is_cached_within_window(self):
        client = mock.Mock()
        client.generate_presigned_url.return_value = 'https://signed.example/a.mp4'
        stub = _Stub('s3://b/media/videos/a.mp4')
        with mock.patch.dict(os.environ, {'MEDIA_DELIVERY_MODE': 's3'}), \
                mock.patch.object(media_url, 'get_s3_client', return_value=client):
            media_url.resolve_media_url(stub)
            media_url.resolve_media_url(stub)
        # 同じ窓なら署名は一度しか作らない。URLが毎回変わるとキャッシュが効かないため。
        self.assertEqual(client.generate_presigned_url.call_count, 1)

    def test_s3_failure_falls_back_to_none(self):
        client = mock.Mock()
        client.generate_presigned_url.side_effect = RuntimeError('boom')
        with mock.patch.dict(os.environ, {'MEDIA_DELIVERY_MODE': 's3'}), \
                mock.patch.object(media_url, 'get_s3_client', return_value=client), \
                mock.patch.object(media_url.logger, 'exception'):
            self.assertIsNone(media_url.resolve_media_url(_Stub('s3://b/a.mp4')))

    def test_cdn_mode_without_keys_falls_back_to_none(self):
        env = {'MEDIA_DELIVERY_MODE': 'cdn'}
        with mock.patch.dict(os.environ, env):
            for k in ('CLOUDFRONT_DOMAIN', 'CLOUDFRONT_KEY_PAIR_ID', 'CLOUDFRONT_PRIVATE_KEY_PATH'):
                os.environ.pop(k, None)
            self.assertIsNone(media_url.resolve_media_url(_Stub('s3://b/a.mp4')))


class PosterUrlTest(SimpleTestCase):
    def setUp(self):
        _clear_caches()

    def test_image_has_no_poster(self):
        self.assertIsNone(media_url.resolve_poster_url(_Stub('s3://b/a.jpg', type='image')))

    def test_unnormalized_video_has_no_poster(self):
        # 正規化バッチ未実施のあいだはサムネイルが存在しないため None。
        with mock.patch.dict(os.environ, {'MEDIA_DELIVERY_MODE': 's3'}):
            self.assertIsNone(
                media_url.resolve_poster_url(_Stub('s3://b/a.mp4', media_version=0))
            )


class ContentSerializerFieldsTest(TestCase):
    def setUp(self):
        _clear_caches()
        self.content = Content.objects.create(
            id='serializer-test', type=Content.TYPE_VIDEO, path='s3://b/media/videos/a.mp4'
        )

    def test_proxy_mode_emits_null_media_url(self):
        # proxy のときは従来どおりフロント側でURLを組み立てる。
        with mock.patch.dict(os.environ, {'MEDIA_DELIVERY_MODE': 'proxy'}):
            data = ContentSerializer(self.content).data
        self.assertIn('media_url', data)
        self.assertIsNone(data['media_url'])
        self.assertIsNone(data['poster_url'])

    def test_serializing_many_does_not_touch_s3(self):
        # 一覧20件で存在確認のI/Oが出ないこと（出ると一覧APIが遅くなる）。
        contents = [self.content] * 20
        with mock.patch.dict(os.environ, {'MEDIA_DELIVERY_MODE': 'proxy'}), \
                mock.patch.object(media_url, 'get_s3_client') as client:
            ContentSerializer(contents, many=True).data
        client.assert_not_called()
