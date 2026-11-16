"""
ランダムなコンテンツを使用して記事を自動生成する

Usage:
    create_random_articles [-n <number>] [--dc <description_count>]

Options:
    -n <number>                 作成する記事数 [default: 10]
    --dc <description_count>    説明文の文字数 [default: 4000]
"""
import os
import random

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "ランダムなコンテンツを使用して記事を自動生成する"

    def add_arguments(self, parser):
        parser.add_argument(
            "-n", type=int, default=10, dest="number",
            help="作成する記事数 (default: 10)",
        )
        parser.add_argument(
            "--dc", type=int, default=4000, dest="description_count",
            help="説明文の文字数 (default: 4000)",
        )

    def handle(self, *args, **options):
        from openai import OpenAI
        from api.models import Article, ArticleTag, Content, User

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            self.stderr.write("エラー: 環境変数 OPENAI_API_KEY を設定してください")
            return

        number = options["number"]
        description_count = options["description_count"]

        client = OpenAI(api_key=api_key)
        auto_user, _ = User.objects.get_or_create(username="auto")

        self.stdout.write(f"記事を {number} 件作成します (説明文: {description_count}字程度)")

        success = 0
        for i in range(number):
            self.stdout.write(f"\n[{i + 1}/{number}] 記事を作成中...")
            try:
                self._create_article(client, auto_user, description_count)
                success += 1
            except Exception as e:
                self.stderr.write(f"  エラー: {e}")

        self.stdout.write(f"\n完了: {success}/{number} 件作成しました")

    def _create_article(self, client, user, description_count: int) -> None:
        from api.models import Article, ArticleTag, Content

        # DMM画像を1〜3件取得（必須）
        dmm_images = list(
            Content.objects.filter(type=Content.TYPE_IMAGE, user="DMM").order_by("?")[:3]
        )
        if not dmm_images:
            raise RuntimeError("DMM画像コンテンツが存在しません")

        # 残りをランダムに補充して合計15件以上にする
        dmm_ids = {c.id for c in dmm_images}
        remaining_needed = max(15 - len(dmm_images), 12)
        other_contents = list(
            Content.objects.exclude(id__in=dmm_ids).order_by("?")[:remaining_needed]
        )

        contents = dmm_images + other_contents
        if len(contents) < 15:
            raise RuntimeError(f"コンテンツ数が不足しています ({len(contents)} 件)")

        # 選定コンテンツの全タグから8個をランダムに取得
        all_tag_names: set[str] = set()
        for c in contents:
            for tag in c.tags.all():
                all_tag_names.add(tag.name)
        tag_names = random.sample(list(all_tag_names), min(8, len(all_tag_names)))

        # コンテンツタイトル一覧をLLMに渡してタイトル生成
        titles_text = "\n".join(
            f"- {c.title}" for c in contents if c.title
        )[:2000]

        title_resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "あなたはアダルトコンテンツのまとめサイトのライターです。"
                        "魅力的で具体的な日本語タイトルを1つだけ出力してください。"
                        "タイトル以外の文字は出力しないこと。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"以下のコンテンツタイトルを参考に、まとめ記事のタイトルを"
                        f"30文字以内で1つ作成してください。\n\n{titles_text}"
                    ),
                },
            ],
            max_tokens=100,
        )
        title = title_resp.choices[0].message.content.strip()
        self.stdout.write(f"  タイトル: {title}")

        # タイトルをもとに説明文生成
        desc_resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "あなたはアダルトコンテンツのまとめサイトのライターです。",
                },
                {
                    "role": "user",
                    "content": (
                        f"「{title}」というタイトルのまとめ記事の説明文を"
                        f"{description_count}字程度で作成してください。"
                    ),
                },
            ],
            max_tokens=3000,
        )
        description = desc_resp.choices[0].message.content.strip()

        # 記事をDBに登録
        article = Article.objects.create(
            title=title,
            description=description,
            user=user,
            thumbnail=dmm_images[0],
        )
        article.contents.set(contents)

        for tag_name in tag_names:
            article_tag, _ = ArticleTag.objects.get_or_create(name=tag_name)
            article_tag.articles.add(article)

        self.stdout.write(f"  登録完了: id={article.id}")
