"""
記事サムネイル作成バッチ

Usage:
  make_article_thumbnails [--dry-run]

Options:
  --dry-run    実際には保存せず対象記事だけ表示する
"""
import os
import random
import string

from django.conf import settings
from django.core.management.base import BaseCommand


def _random_suffix(n=8):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def _extract_middle_frame(video_path: str, save_path: str) -> bool:
    try:
        import cv2
    except ImportError:
        return False

    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total <= 0:
        cap.release()
        return False

    cap.set(cv2.CAP_PROP_POS_FRAMES, total // 2)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        return False

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    ret, buf = cv2.imencode('.jpg', frame)
    if not ret:
        return False
    with open(save_path, 'wb') as f:
        f.write(buf.tobytes())
    return True


class Command(BaseCommand):
    help = "サムネイルがない記事に対してサムネイルを自動生成する"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="実際には保存せず対象記事だけ表示する",
        )

    def handle(self, *args, **options):
        # docopt は batch_shell 経由で使われるが、manage.py から直接呼ぶ場合は
        # add_arguments で定義した argparse が使われる
        dry_run = options["dry_run"]

        from api.models import Article, Content

        articles = Article.objects.filter(thumbnail__isnull=True).prefetch_related("contents")
        self.stdout.write(f"対象記事数: {articles.count()}")

        for article in articles:
            video_contents = [c for c in article.contents.all() if c.type == Content.TYPE_VIDEO]

            if not video_contents:
                self.stdout.write(f"  [SKIP] '{article.title}' - 動画コンテンツなし")
                continue

            chosen = random.choice(video_contents)

            if not chosen.path:
                self.stdout.write(f"  [SKIP] '{article.title}' - パスが空 (content={chosen.id})")
                continue

            video_path = os.path.join(settings.MEDIA_ROOT, chosen.path)
            if not os.path.exists(video_path):
                self.stdout.write(f"  [SKIP] '{article.title}' - ファイル不在: {video_path}")
                continue

            filename = f"thumb_{_random_suffix()}.jpg"
            save_path = os.path.join(settings.MEDIA_ROOT, "images", filename)
            relative_path = f"images/{filename}"

            self.stdout.write(f"  [{'DRY' if dry_run else 'RUN'}] '{article.title}' <- {chosen.path}")

            if dry_run:
                continue

            success = _extract_middle_frame(video_path, save_path)
            if not success:
                self.stdout.write(f"    フレーム抽出失敗")
                continue

            thumb = Content(
                type=Content.TYPE_IMAGE,
                title=f"{article.title}-サムネイル",
                path=relative_path,
                link="",
                source_url=chosen.source_url,
                user=article.user.username,
                description=article.description,
            )
            thumb.save()

            article.thumbnail = thumb
            article.save(update_fields=["thumbnail"])
            self.stdout.write(f"    保存完了: {relative_path} (content={thumb.id})")

        self.stdout.write("完了")
