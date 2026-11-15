"""セキュリティ記事（脆弱性・セキュリティ情報）を Perplexity で自動作成し、Markdown（frontmatter つき）としてフォルダに書き出す。

使い方:
  PERPLEXITY_API_KEY=... python generate_security_articles.py --out-dir <書き出し先> [--existing-dir <dir>]... [--count N] [--tag TAG]...

環境変数: PERPLEXITY_API_KEY（必須）、PERPLEXITY_MODEL（既定 sonar）、SECURITY_ARTICLES_PER_RUN（--count の既定。なければ 3）
終了コード: 0 成功（題材がなく 0 本でも成功）／1 API キーなし・題材選定の失敗・1本も書けず失敗があった／2 引数の誤り
"""

from __future__ import annotations

import os
import sys

from it_news import cli
from it_news.perplexity import Post, urllib_post
from security_news import SECURITY_NEWS

DEFAULT_COUNT = 3
COUNT_ENV = "SECURITY_ARTICLES_PER_RUN"
DEFAULT_TAG = "セキュリティ"


def resolve_count(arg: int | None, env: dict) -> int:
    """--count、なければ SECURITY_ARTICLES_PER_RUN、なければ 3。1〜10 に丸める。"""
    return cli.resolve_count(arg, env, count_env=COUNT_ENV, default=DEFAULT_COUNT)


def main(argv: list[str], env: dict, post: Post = urllib_post) -> int:
    return cli.run_cli(
        argv,
        env,
        post,
        kind=SECURITY_NEWS,
        description="セキュリティ記事を Perplexity で自動作成する",
        default_tag=DEFAULT_TAG,
        count_env=COUNT_ENV,
        default_count=DEFAULT_COUNT,
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], dict(os.environ)))
