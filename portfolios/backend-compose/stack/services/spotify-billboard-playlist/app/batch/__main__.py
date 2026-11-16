"""`python -m app.batch [--add URL ...]` で未処理のチャートURLを処理する。"""

from __future__ import annotations

import argparse
import logging

from app.batch.fetcher import Fetcher
from app.batch.runner import process_pending
from app.config import load_settings
from app.db import Database


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DBに登録されたチャートURLを取得する")
    parser.add_argument(
        "--add", action="append", default=[], metavar="URL", help="処理前にDBへ登録するURL"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    db = Database(load_settings(web=False).db_path)
    for url in args.add:
        db.add_source(url)
    results = process_pending(db, Fetcher())
    for source_id, status in results.items():
        print(f"{source_id}\t{status}\t{len(db.tracks(source_id))} tracks")
    return 1 if "failed" in results.values() else 0


if __name__ == "__main__":
    raise SystemExit(main())
