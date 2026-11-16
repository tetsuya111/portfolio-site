"""S3オブジェクトを別リージョンのバケットへ移し、Content.path を追従させる。

S3バケットのリージョンは作成後に変更できないため、東京へ移すには
「新バケットへコピー → path を差し替え」という手順を踏む必要がある。

1件ずつコピーと path 更新を完了させるため、途中で中断しても整合が保たれ、
再実行すれば続きから処理される（コピー済みのオブジェクトは head_object で検出してスキップする）。
移行の途中でも、新旧どちらのバケットを指す path も再生可能な状態が保たれる。

使い方:
    python manage.py sync_media_region --dest-bucket <新バケット> --dry-run
    python manage.py sync_media_region --dest-bucket <新バケット>
"""
import os

from django.core.management.base import BaseCommand, CommandError

from api.models import Content
from api.s3_client import build_s3_path, get_s3_client, parse_s3_path

# copy_object の上限。これを超えるオブジェクトはマルチパートコピーが必要になる。
COPY_OBJECT_MAX_BYTES = 5 * 1024 * 1024 * 1024


class Command(BaseCommand):
    help = "S3オブジェクトを別リージョンのバケットへコピーし、Content.path を更新する"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dest-bucket",
            default=os.environ.get("MEDIA_S3_BUCKET_NEW", ""),
            help="コピー先バケット名（環境変数 MEDIA_S3_BUCKET_NEW でも指定可）",
        )
        parser.add_argument(
            "--dest-region",
            default=os.environ.get("AWS_REGION") or "ap-northeast-1",
            help="コピー先バケットのリージョン（既定: ap-northeast-1）",
        )
        parser.add_argument(
            "--source-bucket",
            default="",
            help="コピー元バケットを限定する場合に指定（省略時は宛先以外の全バケット）",
        )
        parser.add_argument(
            "--type",
            dest="content_type",
            default="",
            choices=["", "image", "video"],
            help="コンテンツタイプで絞り込む",
        )
        parser.add_argument("-n", "--number", type=int, default=None, help="処理する最大件数")
        parser.add_argument(
            "--dry-run", action="store_true", help="コピーもDB更新も行わず、対象だけを表示する"
        )

    def handle(self, *args, **options):
        dest_bucket = options["dest_bucket"].strip()
        if not dest_bucket:
            raise CommandError("--dest-bucket を指定してください")

        dest_region = options["dest_region"].strip()
        source_bucket = options["source_bucket"].strip()
        dry_run = options["dry_run"]

        dest_s3 = get_s3_client(region=dest_region)
        self._verify_destination(dest_s3, dest_bucket, dest_region)

        qs = Content.objects.exclude(path="")
        if options["content_type"]:
            qs = qs.filter(type=options["content_type"])
        qs = qs.filter(path__startswith="s3://")
        if source_bucket:
            qs = qs.filter(path__startswith=f"s3://{source_bucket}/")

        copied = skipped = already = failed = 0
        processed = 0
        limit = options["number"]

        for content in qs.iterator(chunk_size=200):
            if limit is not None and processed >= limit:
                break

            parsed = parse_s3_path(content.path)
            if not parsed:
                self.stderr.write(f"[SKIP] {content.id} - s3パスとして解釈できません: {content.path}")
                skipped += 1
                continue

            src_bucket, key = parsed
            if src_bucket == dest_bucket:
                skipped += 1
                continue

            processed += 1
            new_path = build_s3_path(dest_bucket, key)

            if dry_run:
                self.stdout.write(f"[DRY] {content.id}: {content.path} -> {new_path}")
                continue

            try:
                if self._exists(dest_s3, dest_bucket, key):
                    # 前回の実行でコピーまでは終わっていたケース。path の更新だけ行う。
                    already += 1
                else:
                    self._copy(dest_s3, src_bucket, key, dest_bucket)
                    copied += 1

                content.path = new_path
                content.save(update_fields=["path"])
                self.stdout.write(f"[OK] {content.id} -> {new_path}")
            except Exception as e:
                self.stderr.write(f"[ERROR] {content.id} ({key}): {e}")
                failed += 1

        if dry_run:
            self.stderr.write(f"\n[DRY RUN] 対象 {processed}件 / 対象外 {skipped}件")
        else:
            self.stderr.write(
                f"\n完了: コピー {copied}件 / コピー済み {already}件 / "
                f"対象外 {skipped}件 / エラー {failed}件"
            )
            if failed:
                self.stderr.write("エラーが残っています。再実行すると未処理分から続行します。")

    def _verify_destination(self, s3, bucket: str, expected_region: str) -> None:
        """宛先バケットの存在とリージョンを確認する。バケットの作成はこのコマンドでは行わない。"""
        try:
            s3.head_bucket(Bucket=bucket)
        except Exception as e:
            raise CommandError(
                f"コピー先バケット {bucket} にアクセスできません: {e}\n"
                f"先に {expected_region} にバケットを作成し、認証情報に権限を付与してください。"
            )

        try:
            location = s3.get_bucket_location(Bucket=bucket).get("LocationConstraint")
        except Exception:
            return  # 権限がない場合は確認を諦める（コピー自体は可能なことがある）

        # us-east-1 のみ None が返る仕様。
        actual = location or "us-east-1"
        if actual != expected_region:
            raise CommandError(
                f"コピー先バケット {bucket} は {actual} にあります（指定は {expected_region}）。"
                f"リージョンを取り違えたまま移行すると遅延が改善しません。"
            )

    def _exists(self, s3, bucket: str, key: str) -> bool:
        try:
            s3.head_object(Bucket=bucket, Key=key)
            return True
        except Exception:
            return False

    def _copy(self, dest_s3, src_bucket: str, key: str, dest_bucket: str) -> None:
        """リージョンをまたぐサーバ間コピー。ローカルを経由しない。"""
        src_s3 = get_s3_client(bucket=src_bucket)
        head = src_s3.head_object(Bucket=src_bucket, Key=key)
        size = head.get("ContentLength", 0)
        if size > COPY_OBJECT_MAX_BYTES:
            raise RuntimeError(
                f"{size} バイトは copy_object の上限(5GB)を超えています。"
                "マルチパートコピーが必要です。"
            )

        dest_s3.copy_object(
            Bucket=dest_bucket,
            Key=key,
            CopySource={"Bucket": src_bucket, "Key": key},
            MetadataDirective="COPY",
        )
