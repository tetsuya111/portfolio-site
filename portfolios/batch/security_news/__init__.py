"""セキュリティ記事（脆弱性・セキュリティ情報）の自動作成。共通の処理は it_news を使う。"""

from it_news.generate import ArticleKind

from .markdown import build_security_markdown
from .prompts import article_request, topics_request, validate_article

# 脆弱性は公表から報道・アドバイザリの更新まで時間がかかるため、IT ニュース（day / week）より広く検索する
SECURITY_NEWS = ArticleKind(
    topics_request=topics_request,
    article_request=article_request,
    validate_article=validate_article,
    build_markdown=build_security_markdown,
    topics_recency="week",
    article_recency="month",
    fallback_slug="security-news",
)
