"""IT ニュースの記事を Perplexity で自動作成し、Markdown（frontmatter つき）としてフォルダに書き出す。

使い方:
  PERPLEXITY_API_KEY=... python generate_it_articles.py --out-dir <書き出し先> [--existing-dir <dir>]... [--count N] [--tag TAG]...

環境変数: PERPLEXITY_API_KEY（必須）、PERPLEXITY_MODEL（既定 sonar）、IT_ARTICLES_PER_RUN（--count の既定。なければ 5）
終了コード: 0 成功（題材がなく 0 本でも成功）／1 API キーなし・題材選定の失敗・1本も書けず失敗があった／2 引数の誤り
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from it_news.generate import run_generation
from it_news.perplexity import PerplexityError, Post, urllib_post

DEFAULT_COUNT = 5
MIN_COUNT, MAX_COUNT = 1, 10
DEFAULT_TAG = "IT ニュース"


def resolve_count(arg: int | None, env: dict) -> int:
    """--count、なければ IT_ARTICLES_PER_RUN、なければ 5。1〜10 に丸める。"""
    value = arg
    if value is None:
        try:
            value = int(env.get("IT_ARTICLES_PER_RUN", DEFAULT_COUNT))
        except ValueError:
            value = DEFAULT_COUNT
    return max(MIN_COUNT, min(MAX_COUNT, value))


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="IT ニュースの記事を Perplexity で自動作成する")
    p.add_argument("--out-dir", required=True, type=Path, help="記事の書き出し先（既存の記事は重複判定にも使う）")
    p.add_argument("--existing-dir", action="append", default=[], type=Path, help="重複判定に加えるフォルダ（複数可）")
    p.add_argument("--count", type=int, help=f"作る記事の数（{MIN_COUNT}〜{MAX_COUNT}）")
    p.add_argument("--tag", action="append", help=f"全記事に付けるタグ（複数可。既定「{DEFAULT_TAG}」）")
    return p.parse_args(argv)


def main(argv: list[str], env: dict, post: Post = urllib_post) -> int:
    args = parse_args(argv)
    api_key = env.get("PERPLEXITY_API_KEY", "").strip()
    if not api_key:
        print("PERPLEXITY_API_KEY が設定されていません")
        return 1
    model = env.get("PERPLEXITY_MODEL", "").strip() or "sonar"
    count = resolve_count(args.count, env)
    try:
        result = run_generation(
            post=post,
            api_key=api_key,
            model=model,
            count=count,
            out_dir=args.out_dir,
            existing_dirs=args.existing_dir,
            tags=args.tag or [DEFAULT_TAG],
            now=datetime.now(timezone.utc),
        )
    except (PerplexityError, ValueError) as e:
        print(f"題材を選べませんでした: {e}")
        return 1
    print(f"作成 {len(result.written)} 本・失敗 {len(result.failed)} 本・出典の重複で除外 {result.skipped} 件")
    return 1 if result.failed and not result.written else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], dict(os.environ)))
