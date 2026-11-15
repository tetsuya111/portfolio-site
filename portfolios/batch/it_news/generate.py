"""題材選定 → 重複除外 → 記事執筆 → md の書き出し。記事の種類（ArticleKind）でプロンプトと md の形を切り替える。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from .files import FALLBACK_SLUG, choose_file_name, load_existing, normalize_url
from .markdown import build_article_markdown
from .perplexity import PerplexityError, Post, call_perplexity
from .prompts import article_request, topics_request, validate_article, validate_topics

JST = timezone(timedelta(hours=9))


@dataclass(frozen=True)
class ArticleKind:
    """記事の種類ごとに変わる部分。題材の検証（validate_topics）と重複除外・書き出しは共通。

    - topics_request(recent_titles) / article_request(topic) -> (messages, JSON スキーマ)
    - validate_article(data) -> 記事の dict（不正なら ValueError）
    - build_markdown(*, article, references, date, source_url, generator, tags) -> md（不正なら ValueError）
    """

    topics_request: Callable[[list[str]], tuple[list[dict], dict]]
    article_request: Callable[[dict], tuple[list[dict], dict]]
    validate_article: Callable[[object], dict]
    build_markdown: Callable[..., str]
    topics_recency: str = "day"
    article_recency: str = "week"
    fallback_slug: str = FALLBACK_SLUG


IT_NEWS = ArticleKind(
    topics_request=topics_request,
    article_request=article_request,
    validate_article=validate_article,
    build_markdown=build_article_markdown,
)


@dataclass
class Result:
    written: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    skipped: int = 0  # 既存記事・同じ実行内で出典が重なったため除いた題材の数


def jst_date(now: datetime) -> str:
    """記事の日付（日本時間の暦日）。"""
    return now.astimezone(JST).strftime("%Y-%m-%d")


def run_generation(
    *,
    post: Post,
    api_key: str,
    model: str,
    count: int,
    out_dir: Path,
    existing_dirs: list[Path],
    tags: list[str],
    now: datetime,
    log: Callable[[str], None] = print,
    kind: ArticleKind = IT_NEWS,
) -> Result:
    """最大 count 本の記事を out_dir に書き出す。記事ごとの失敗は記録して次へ進む（題材選定の失敗は例外）。"""
    result = Result()
    existing = load_existing([out_dir, *existing_dirs])
    taken = set(existing.names)
    seen = set(existing.source_urls)
    date = jst_date(now)

    messages, schema = kind.topics_request(existing.recent_titles)
    data, search_refs = call_perplexity(
        post=post, api_key=api_key, model=model, messages=messages, schema=schema, recency=kind.topics_recency
    )
    # 題材が 0 件のとき、検索で何も見つからなかったのか（recency が狭い）、見つかったが選ばれなかったのか（プロンプト）を見分ける
    log(f"題材の検索で参照したページ: {len(search_refs)} 件")
    topics = sorted(validate_topics(data, log=log), key=lambda t: t["importance"], reverse=True)

    candidates = []
    for t in topics:
        key = normalize_url(t["sourceUrl"])
        if key in seen:
            result.skipped += 1
            continue
        seen.add(key)
        candidates.append(t)
    log(f"題材の候補 {len(topics)} 件のうち {len(candidates)} 件が未掲載です（出典の重複で除外 {result.skipped} 件）")

    # 重要度の高い順に書き、失敗したら次の候補で補う。API の呼び出しが増えすぎないよう、試すのは count の 2 倍まで
    out_dir.mkdir(parents=True, exist_ok=True)
    for t in candidates[: count * 2]:
        if len(result.written) >= count:
            break
        try:
            messages, schema = kind.article_request(t)
            data, references = call_perplexity(
                post=post, api_key=api_key, model=model, messages=messages, schema=schema, recency=kind.article_recency
            )
            article = kind.validate_article(data)
            md = kind.build_markdown(
                article=article,
                references=references,
                date=date,
                source_url=t["sourceUrl"],
                generator=f"perplexity/{model}",
                tags=tags,
            )
        except (PerplexityError, ValueError) as e:
            result.failed.append(t["title"])
            log(f"記事を作れませんでした「{t['title']}」: {e}")
            continue
        name = choose_file_name(date, article["slug"], taken, kind.fallback_slug)
        taken.add(name)
        path = out_dir / f"{name}.md"
        path.write_text(md, encoding="utf-8", newline="\n")
        result.written.append(str(path))
        log(f"書き出しました: {path}")
    return result
