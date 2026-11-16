import hashlib
import subprocess
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import Content, ContentDetail, Series, Tag

def_segment_time = 15  # 15秒ごとに分割
skip_time = 20.0  # 20秒以下の動画は分割せずにスキップ

class Command(BaseCommand):
    help = "動画をショート形式(15秒)に分割してデータベースに再登録する"

    def add_arguments(self, parser):
        parser.add_argument("-n", "--number", type=int, default=None, help="処理する動画数")

    def handle(self, *args, **options):
        number = options["number"]
        video_dir = Path(settings.MEDIA_ROOT) / "videos"

        qs = Content.objects.filter(type=Content.TYPE_VIDEO)
        if number:
            qs = qs[:number]

        for content in list(qs):
            filepath = self._resolve_path(content, video_dir)
            if not filepath:
                self.stderr.write(f"ファイルが見つかりません: {content.id} path={content.path}")
                continue

            duration = self._get_duration(filepath)
            if duration is None:
                self.stderr.write(f"再生時間取得失敗: {filepath}")
                continue

            if duration <= skip_time:
                self.stdout.write(f"スキップ (15秒以下): {filepath.name}")
                continue

            self.stdout.write(f"分割処理: {filepath.name} ({duration:.1f}秒)")
            with TemporaryDirectory() as tmpdir:
                chunks = self._split_video(filepath, Path(tmpdir))
                if not chunks:
                    self.stderr.write(f"分割失敗: {filepath.name}")
                    continue
                
                chunks=self._resplit_video(chunks)

                series_id = self._new_series_id()
                original_tags = list(content.tags.all())

                for i, chunk_path in enumerate(chunks):
                    dst_chunk_path = video_dir / chunk_path.name
                    shutil.copy(chunk_path, dst_chunk_path)    # 一時ファイルから元ファイルと同じ場所にコピー
                    chunk_path = dst_chunk_path  # コピー後のパスを使用
                    chunk_title = f"{content.title} - {i}"
                    print("再生時間 :",self._get_duration(chunk_path))
                    self._save_chunk(chunk_path, content, series_id, i, chunk_title, original_tags)

                filepath.unlink(missing_ok=True)
                content.delete()
                self.stdout.write(f"  元動画削除: {filepath.name}")

    def _resolve_path(self, content: Content, video_dir: Path) -> Path | None:
        if not content.path:
            return None
        candidates = [
            Path(content.path),
            Path(settings.MEDIA_ROOT) / content.path,
            video_dir / Path(content.path).name,
        ]
        for p in candidates:
            if p.exists():
                return p
        return None

    def _get_duration(self, filepath: Path) -> float | None:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(filepath),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception as e:
            self.stderr.write(f"ffprobeエラー: {e}")
            return None

    def _split_video(self, filepath: Path, output_dir: Path, segment_time=def_segment_time) -> list[Path]:
        stem = filepath.stem
        output_pattern = str(output_dir / f"{stem}_part%03d.mp4")
        cmd = [
            "ffmpeg", "-i", str(filepath),
            "-c", "copy",
            "-map", "0",
            "-segment_time", str(segment_time),
            "-segment_time_delta", "0.05",
            "-f", "segment",
            "-reset_timestamps", "1",
            output_pattern,
            "-y",
        ]
        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            self.stderr.write(f"ffmpegエラー: {e.stderr.decode(errors='replace')}")
            return []
        return sorted(output_dir.glob(f"{stem}_part*.mp4"))
    def _resplit_video(self, chunks: list[Path]) -> list[Path]:
        def _():
            for chunk in chunks:
                duration = self._get_duration(chunk)
                if duration <= skip_time:
                # スキップ時間以下、正常
                    print(f"正常: {chunk.name} ({duration:.1f}秒)")
                    yield chunk
                else:
                # スキップ時間超、再分割
                    print(f"再分割: {chunk.name} ({duration:.1f}秒)")
                    yield from self._split_video(chunk, chunk.parent,segment_time=def_segment_time//2)
        yield from _()
    def _new_series_id(self) -> str:
        existing = set(Series.objects.values_list("series_id", flat=True))
        while True:
            sid = uuid.uuid4().hex[:8]
            if sid not in existing:
                return sid

    def _save_chunk(
        self,
        chunk_path: Path,
        original: Content,
        series_id: str,
        series_number: int,
        title: str,
        tags: list,
    ) -> None:
        path_str = str(chunk_path)
        content_id = hashlib.sha256(f"{path_str}{original.link}{title}".encode()).hexdigest()[:32]
        obj, created = Content.objects.get_or_create(
            id=content_id,
            defaults={
                "type": Content.TYPE_VIDEO,
                "title": title,
                "path": path_str,
                "link": original.link,
                "source_url": original.source_url,
                "user": original.user,
                "description": original.description,
            },
        )
        if created:
            series_obj, _ = Series.objects.get_or_create(series_id=series_id)
            ContentDetail.objects.create(
                content=obj,
                series=series_obj,
                series_number=series_number,
            )
            for tag in tags:
                tag.contents.add(obj)
            self.stdout.write(f"  登録: {title}")
        else:
            self.stdout.write(f"  既存: {title}")
