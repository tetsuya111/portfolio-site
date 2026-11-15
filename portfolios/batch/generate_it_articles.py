"""IT ニュースの記事を Perplexity で自動作成し、Markdown（frontmatter つき）としてフォルダに書き出す。

使い方:
  PERPLEXITY_API_KEY=... python generate_it_articles.py --out-dir <書き出し先> [--existing-dir <dir>]... [--count N] [--tag TAG]...

環境変数: PERPLEXITY_API_KEY（必須）、PERPLEXITY_MODEL（既定 sonar）、IT_ARTICLES_PER_RUN（--count の既定。なければ 5）
終了コード: 0 成功（題材がなく 0 本でも成功）／1 API キーなし・題材選定の失敗・1本も書けず失敗があった／2 引数の誤り
"""

from __future__ import annotations

import os
import sys

from it_news import cli
from it_news.generate import IT_NEWS
from it_news.perplexity import Post, urllib_post

DEFAULT_COUNT = 5
COUNT_ENV = "IT_ARTICLES_PER_RUN"
DEFAULT_TAG = "IT ニュース"


def resolve_count(arg: int | None, env: dict) -> int:
    """--count、なければ IT_ARTICLES_PER_RUN、なければ 5。1〜10 に丸める。"""
    return cli.resolve_count(arg, env, count_env=COUNT_ENV, default=DEFAULT_COUNT)


def main(argv: list[str], env: dict, post: Post = urllib_post) -> int:
    return cli.run_cli(
        argv,
        env,
        post,
        kind=IT_NEWS,
        description="IT ニュースの記事を Perplexity で自動作成する",
        default_tag=DEFAULT_TAG,
        count_env=COUNT_ENV,
        default_count=DEFAULT_COUNT,
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], dict(os.environ)))
