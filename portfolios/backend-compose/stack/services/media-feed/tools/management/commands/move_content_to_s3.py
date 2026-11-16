import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from boto3.s3.transfer import TransferConfig

from api.models import Content
from api.s3_client import DEFAULT_BUCKET, build_s3_path, get_s3_client, is_s3_path

# アップロード先バケット。環境変数 MEDIA_S3_BUCKET で切り替える。
BUCKET_NAME = DEFAULT_BUCKET


transfer_config = TransferConfig(
    multipart_threshold=1024 * 1024 * 25,   # 25MB以上でマルチパート開始
    multipart_chunksize=1024 * 1024 * 25,   # 各チャンクを25MB
    max_concurrency=5,
    use_threads=True
)


def _is_s3_path(path: str) -> bool:
    return is_s3_path(path)


def _make_s3_client():
    if not (os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY")):
        raise ValueError("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set in environment variables")
    return get_s3_client(bucket=BUCKET_NAME)


class Command(BaseCommand):
    help = "コンテンツをローカルからS3に移動してDBのpathを更新する"

    def add_arguments(self, parser):
        parser.add_argument("--title", "-t", default="", help="タイトル（部分一致）")
        parser.add_argument(
            "--tags", default="", help="タグ（カンマ区切り、AND検索）"
        )
        parser.add_argument(
            "--type",
            dest="content_type",
            default="",
            choices=["", "image", "video"],
            help="コンテンツタイプ (image / video)。省略時は全て",
        )
        parser.add_argument("--user", "-u", default="", help="Content.user の値")
        parser.add_argument(
            "--number", "-n", type=int, default=None, help="対象とするコンテンツ数"
        )

    def handle(self, *args, **options):
        qs = Content.objects.all()

        if options["title"]:
            qs = qs.filter(title__icontains=options["title"])

        if options["tags"]:
            for tag_name in [t.strip() for t in options["tags"].split(",") if t.strip()]:
                qs = qs.filter(tags__name=tag_name)

        if options["content_type"]:
            qs = qs.filter(type=options["content_type"])

        if options["user"]:
            qs = qs.filter(user=options["user"])

        if options["number"] is not None:
            qs = qs[: options["number"]]

        total = qs.count() if hasattr(qs, "count") else len(qs)
        self.stderr.write(f"対象コンテンツ数: {total}")

        s3 = _make_s3_client()
        ok = skip = error = 0

        for content in qs:
            if not content.path or _is_s3_path(content.path):
                self.stderr.write(f"[SKIP] {content.id} - pathなし or 既にS3")
                skip += 1
                continue

            local_path = Path(settings.MEDIA_ROOT) / content.path
            if not local_path.exists():
                self.stderr.write(f"[SKIP] {content.id} - ファイル不在: {local_path}")
                skip += 1
                continue

            type_dir = "images" if content.type == Content.TYPE_IMAGE else "videos"
            s3_key = f"media/{type_dir}/{local_path.name}"
            s3_path = build_s3_path(BUCKET_NAME, s3_key)

            try:
                s3.upload_file(str(local_path), BUCKET_NAME, s3_key,Config=transfer_config)
                content.path = s3_path
                content.save(update_fields=["path"])
                self.stdout.write(f"[OK] {content.id} -> {s3_path}")
                self.stdout.write(f"[タイトル] {content.title}")
                ok += 1
            except Exception as e:
                self.stderr.write(f"[ERROR] {content.id}: {e}")
                error += 1

        self.stderr.write(f"\n完了: {ok}件移動, {skip}件スキップ, {error}件エラー")
