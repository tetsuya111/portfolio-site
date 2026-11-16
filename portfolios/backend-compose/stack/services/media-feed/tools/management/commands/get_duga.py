import csv
import hashlib
import os
import sqlite3
import time
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from api.models import Content, Tag

DUGA_USER = "DUGA"
CSV_PATH = Path(__file__).resolve().parents[4] / "others" / "productcustom.csv"
DB_PATH = Path(__file__).resolve().parents[4] / "db" / "duga_all_items.sqlite3"
VIDEO_DIR = Path(settings.MEDIA_ROOT) / "videos"
IMAGE_DIR = Path(settings.MEDIA_ROOT) / "images"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# CSVカラム名
COL_ID = "商品ID"
COL_TITLE = "タイトル"
COL_DESC = "紹介文"
COL_LABEL = "レーベル名"
COL_MAKER = "メーカー名"
COL_CATEGORY = "カテゴリ"
COL_CAST = "出演者"


# ────────────────────────────────────────────────────────────
# ヘルパー
# ────────────────────────────────────────────────────────────

def _get_db_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(DB_PATH))


def _video_url(product_id: str) -> str:
    return f"https://affsample.duga.jp/unsecure/{product_id}/noauth/movie.mp4"


def _source_url(product_id: str, affiliate_id: str) -> str:
    return f"https://click.duga.jp/ppv/{product_id}/{affiliate_id}-01"


def _split_product_id(product_id: str):
    """'abc-0001' → ('abc', '0001')"""
    parts = product_id.rsplit("-", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return product_id, "0000"


def _image_url(product_id: str, img_num: int) -> str:
    prefix, number = _split_product_id(product_id)
    return f"https://pic.duga.jp/unsecure/{prefix}/{number}/cap/{img_num:04d}.jpg"
def _image_url2(product_id: str, img_num: int) -> str:
    prefix, number = _split_product_id(product_id)
    return f"https://pic.duga.jp/unsecure/{prefix}/{number}/noauth/scap/{img_num:03d}.jpg"


def _save_file(url: str, save_dir: Path, product_id: str, suffix: str) -> str | None:
    """ファイルをダウンロードして保存。相対パスを返す。"""
    save_dir.mkdir(parents=True, exist_ok=True)
    safe_id = product_id.replace("/", "_")
    filename = f"duga_{safe_id}{suffix}"
    save_path = save_dir / filename
    if save_path.exists():
        rel = str(save_path.relative_to(settings.MEDIA_ROOT))
        return rel
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30, stream=True)
        if resp.status_code != 200:
            return None
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 64):
                f.write(chunk)
        return str(save_path.relative_to(settings.MEDIA_ROOT))
    except Exception:
        return None


def _register_content(row: dict, content_type: str, path: str, link: str, affiliate_id: str):
    """ContentモデルをDBに登録。タグもセット。"""
    source_url = _source_url(row[COL_ID], affiliate_id)

    content = Content(
        type=content_type,
        title=row.get(COL_TITLE, ""),
        path=path,
        link=link,
        source_url=source_url,
        user=DUGA_USER,
        description=row.get(COL_DESC, ""),
    )
    content.save()

    tag_names = []
    for col in [COL_LABEL, COL_MAKER, COL_CATEGORY, COL_CAST]:
        val = row.get(col, "").strip()
        if val:
            # 出演者は複数いる場合がある（カンマ/スペース区切り）
            for name in [v.strip() for v in val.replace("、", ",").split(",") if v.strip()]:
                tag_names.append(name)

    for name in tag_names:
        tag, _ = Tag.objects.get_or_create(name=name[:100])
        tag.contents.add(content)

    return content


# ────────────────────────────────────────────────────────────
# データDB作成処理
# ────────────────────────────────────────────────────────────

def _make_db(command):
    if not CSV_PATH.exists():
        command.stderr.write(f"CSVファイルが見つかりません: {CSV_PATH}")
        return

    command.stderr.write(f"CSV読み込み中: {CSV_PATH}")
    rows = []
    for enc in ["cp932", "utf-8-sig", "utf-8"]:
        try:
            with open(CSV_PATH, encoding=enc, newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                columns = reader.fieldnames or []
            command.stderr.write(f"エンコーディング: {enc}, 件数: {len(rows)}")
            break
        except (UnicodeDecodeError, Exception):
            continue

    if not rows:
        command.stderr.write("CSVの読み込みに失敗しました")
        return

    conn = _get_db_conn()
    cur = conn.cursor()

    col_defs = ", ".join(f'"{c}" TEXT' for c in columns)
    cur.execute(f"DROP TABLE IF EXISTS products")
    cur.execute(f"CREATE TABLE products ({col_defs})")

    placeholders = ", ".join("?" * len(columns))
    for row in rows:
        values = [row.get(c, "") for c in columns]
        cur.execute(f"INSERT INTO products VALUES ({placeholders})", values)

    conn.commit()
    conn.close()
    command.stdout.write(f"データDB作成完了: {DB_PATH} ({len(rows)}件)")


# ────────────────────────────────────────────────────────────
# DB検索
# ────────────────────────────────────────────────────────────

def _search_db(keyword: str, number: int | None,random_=True) -> list[dict]:
    if not DB_PATH.exists():
        return []
    conn = _get_db_conn()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if keyword:
        q = f"%{keyword}%"
        sql = (
            f'SELECT * FROM products WHERE "{COL_TITLE}" LIKE ? '
            f'OR "{COL_DESC}" LIKE ? OR "{COL_CATEGORY}" LIKE ? OR "{COL_CAST}" LIKE ?'
        )
        params: list = [q, q, q, q]
    else:
        sql = "SELECT * FROM products"
        params = []

    if number:
        sql += f" LIMIT {int(number)}"
    
    if random_:
        sql += " ORDER BY RANDOM()"

    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ────────────────────────────────────────────────────────────
# 動画取得処理
# ────────────────────────────────────────────────────────────

def _get_videos(command, keyword: str, number: int | None, affiliate_id: str):
    rows = _search_db(keyword, number)
    command.stderr.write(f"対象商品数: {len(rows)}")

    ok = skip = error = 0
    for row in rows:
        product_id = row.get(COL_ID, "").strip()
        if not product_id:
            skip += 1
            continue

        # 既登録チェック
        video_url = _video_url(product_id)
        if Content.objects.filter(link=video_url).exists():
            command.stderr.write(f"[SKIP] 既登録: {product_id}")
            skip += 1
            continue

        suffix = ".mp4"
        path = _save_file(video_url, VIDEO_DIR, product_id, suffix)
        if path is None:
            command.stderr.write(f"[ERROR] ダウンロード失敗: {video_url}")
            error += 1
            continue

        try:
            content = _register_content(row, Content.TYPE_VIDEO, path, video_url, affiliate_id)
            command.stdout.write(f"[OK] {product_id} -> {content.id}")
            command.stdout.write(f"title,{content.title},path,{path}")
            ok += 1
        except Exception as e:
            command.stderr.write(f"[ERROR] DB登録失敗 {product_id}: {e}")
            error += 1

        time.sleep(0.5)

    command.stderr.write(f"\n完了: {ok}件登録, {skip}件スキップ, {error}件エラー")


# ────────────────────────────────────────────────────────────
# 画像取得処理
# ────────────────────────────────────────────────────────────

def _fetch_image_urls(product_id: str) -> list[str]:
    """画像パス一覧を取得する（連番で存在確認）。"""
    urls = []
    img_num = 1
    def image_exists(url: str) -> bool:
        try:
            resp = requests.head(url, headers=HEADERS, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False
    while True:
        url = _image_url(product_id, img_num)
        print("log.. imageurl:", url)
        if image_exists(url):
            urls.append(url)
            img_num += 1
        else:
            break
            """
            #画質が低い
            url = _image_url2(product_id, img_num)
            print("log.. imageurl2:", url)
            if image_exists(url):
                urls.append(url)
                img_num += 1
            else: 
                break
            """
    return urls


def _get_images(command, keyword: str, number: int | None, affiliate_id: str):
    rows = _search_db(keyword, number)
    command.stderr.write(f"対象商品数: {len(rows)}")

    ok = skip = error = 0
    for row in rows:
        product_id = row.get(COL_ID, "").strip()
        if not product_id:
            skip += 1
            continue

        image_urls = _fetch_image_urls(product_id)
        if not image_urls:
            command.stderr.write(f"[SKIP] 画像なし: {product_id}")
            skip += 1
            continue

        for i, img_url in enumerate(image_urls):
            if Content.objects.filter(link=img_url).exists():
                continue
            suffix = f"_{i+1:04d}.jpg"
            path = _save_file(img_url, IMAGE_DIR, product_id, suffix)
            if path is None:
                error += 1
                continue
            try:
                content = _register_content(row, Content.TYPE_IMAGE, path, img_url, affiliate_id)
                command.stdout.write(f"[OK] {product_id}[{i+1}] -> {content.id}")
                ok += 1
            except Exception as e:
                command.stderr.write(f"[ERROR] DB登録失敗 {product_id}: {e}")
                error += 1

        time.sleep(0.3)

    command.stderr.write(f"\n完了: {ok}件登録, {skip}件スキップ, {error}件エラー")


# ────────────────────────────────────────────────────────────
# コマンド
# ────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "DUGAのデータDB作成・動画/画像取得・Content登録"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="subcommand")

        # make
        subparsers.add_parser("make", help="全データCSVからデータDBを作成する")

        # videos
        videos_parser = subparsers.add_parser("videos", help="動画タイプのContentを登録する")
        videos_parser.add_argument("-k", "--keyword", default="", help="キーワード（タイトル・説明・カテゴリ・出演者）")
        videos_parser.add_argument("-n", "--number", type=int, default=None, help="取得する商品数")

        # images
        images_parser = subparsers.add_parser("images", help="画像タイプのContentを登録する")
        images_parser.add_argument("-k", "--keyword", default="", help="キーワード（タイトル・説明・カテゴリ・出演者）")
        images_parser.add_argument("-n", "--number", type=int, default=None, help="取得する商品数")

    def handle(self, *args, **options):
        subcommand = options.get("subcommand")

        if subcommand == "make":
            _make_db(self)

        elif subcommand in ("videos", "images"):
            affiliate_id = os.environ.get("DUGA_AFFILIATE_ID", "")
            if not affiliate_id:
                self.stderr.write("エラー: 環境変数 DUGA_AFFILIATE_ID を設定してください")
                return
            keyword = options.get("keyword", "")
            number = options.get("number")
            if not DB_PATH.exists():
                self.stderr.write(f"データDBが見つかりません。先に `get_duga make` を実行してください: {DB_PATH}")
                return
            if subcommand == "videos":
                _get_videos(self, keyword, number, affiliate_id)
            else:
                _get_images(self, keyword, number, affiliate_id)

        else:
            self.stdout.write(self.style.WARNING(
                "Usage:\n"
                "  python manage.py get_duga make\n"
                "  python manage.py get_duga videos [-k <keyword>] [-n <number>]\n"
                "  python manage.py get_duga images [-k <keyword>] [-n <number>]\n"
            ))
