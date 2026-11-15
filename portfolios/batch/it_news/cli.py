"""記事作成 CLI の共通部分（引数・API キー・本数の決定・終了コード）。記事の種類ごとの入口から呼ぶ。

終了コード: 0 成功（題材がなく 0 本でも成功）／1 API キーなし・題材選定の失敗・1本も書けず失敗があった／2 引数の誤り
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from .generate import ArticleKind, run_generation
from .perplexity import PerplexityError, Post

MIN_COUNT, MAX_COUNT = 1, 10


def resolve_count(arg: int | None, env: dict, *, count_env: str, default: int, minimum: int = MIN_COUNT) -> int:
    """--count、なければ環境変数 count_env、なければ default。minimum（既定 1）〜10 に丸める。"""
    value = arg
    if value is None:
        try:
            value = int(env.get(count_env, default))
        except ValueError:
            value = default
    return max(minimum, min(MAX_COUNT, value))


def parse_args(argv: list[str], description: str, default_tag: str) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--out-dir", required=True, type=Path, help="記事の書き出し先（既存の記事は重複判定にも使う）")
    p.add_argument("--existing-dir", action="append", default=[], type=Path, help="重複判定に加えるフォルダ（複数可）")
    p.add_argument("--count", type=int, help=f"作る記事の数（最大 {MAX_COUNT}）")
    p.add_argument("--tag", action="append", help=f"全記事に付けるタグ（複数可。既定「{default_tag}」）")
    return p.parse_args(argv)


def run_cli(
    argv: list[str],
    env: dict,
    post: Post,
    *,
    kind: ArticleKind,
    description: str,
    default_tag: str,
    count_env: str,
    default_count: int,
    min_count: int = MIN_COUNT,
) -> int:
    """min_count を 0 にすると、本数 0 で「作らない」を表せる（API を呼ばずに終了コード 0）。"""
    args = parse_args(argv, description, default_tag)
    count = resolve_count(args.count, env, count_env=count_env, default=default_count, minimum=min_count)
    if count == 0:
        print(f"作る記事の数が 0 のため、作成を省略します（{count_env} / --count）")
        return 0
    api_key = env.get("PERPLEXITY_API_KEY", "").strip()
    if not api_key:
        print("PERPLEXITY_API_KEY が設定されていません")
        return 1
    model = env.get("PERPLEXITY_MODEL", "").strip() or "sonar"
    try:
        result = run_generation(
            post=post,
            api_key=api_key,
            model=model,
            count=count,
            out_dir=args.out_dir,
            existing_dirs=args.existing_dir,
            tags=args.tag or [default_tag],
            now=datetime.now(timezone.utc),
            kind=kind,
        )
    except (PerplexityError, ValueError) as e:
        print(f"題材を選べませんでした: {e}")
        return 1
    print(f"作成 {len(result.written)} 本・失敗 {len(result.failed)} 本・出典の重複で除外 {result.skipped} 件")
    return 1 if result.failed and not result.written else 0
