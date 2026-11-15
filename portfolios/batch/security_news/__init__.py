"""セキュリティ記事（脆弱性・セキュリティ情報）の自動作成。共通の処理は it_news を使う。"""

from it_news.generate import ArticleKind

from .markdown import build_security_markdown
from .prompts import article_request, topics_request, validate_article

# 題材は IT ニュースと同じく直近（day）から選ぶ（毎日の実行で同じ脆弱性が別の出典 URL で選ばれ直すのを減らす）。
# 記事の執筆は、アドバイザリ・パッチの情報まで拾えるよう広く（month）検索する
SECURITY_NEWS = ArticleKind(
    topics_request=topics_request,
    article_request=article_request,
    validate_article=validate_article,
    build_markdown=build_security_markdown,
    topics_recency="day",
    article_recency="month",
    fallback_slug="security-news",
)
