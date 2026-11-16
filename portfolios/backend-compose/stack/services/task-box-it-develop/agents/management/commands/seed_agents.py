from pathlib import Path

from django.core.management.base import BaseCommand

from agents.models import AgentConfig, PromptTemplate

SEED_DIR = Path(__file__).resolve().parents[2] / "seed_prompts"

AGENTS = [
    {
        "key": AgentConfig.HEARING,
        "name": "ヒアリング",
        "callable_from_chat": False,
        "call_description": "",
    },
    {
        "key": AgentConfig.SUMMARY,
        "name": "要件サマリーのプレビュー",
        "callable_from_chat": True,
        "call_description": (
            "これまでの対話から要件サマリーのプレビューを作成する。顧客が、要件サマリーや"
            "要件定義のプレビュー・作成・出力を求めたときに呼ぶ。"
        ),
    },
    {
        "key": AgentConfig.MARKET_ESTIMATE,
        "name": "相場見積もり",
        "callable_from_chat": True,
        "call_description": (
            "一般的な業者に依頼した場合の相場の見積もりを作成する。顧客が、相場・世間一般の"
            "費用感・一般的な業者に頼んだ場合の予算を求めたときに呼ぶ。"
        ),
    },
    {
        "key": AgentConfig.SELF_ESTIMATE,
        "name": "自分見積もり",
        "callable_from_chat": True,
        "call_description": (
            "この会社（タスク百葉箱）に依頼した場合の見積もりを作成する。顧客が、この会社での"
            "見積もり・ここに頼んだ場合の費用を求めたときに呼ぶ。"
        ),
    },
]

TEMPLATES = [
    ("見積もり（相場）", "相場の見積もりをして。"),
    ("見積もり（自分）", "この会社で見積もりして。"),
    (
        "要件サマリーの項目の確認",
        "これまで入力した情報から要件サマリーの項目を取得し、一覧形式で表示して\n"
        "項目名と値をどちらも表示して。値がない場合は「なし」と出力して。項目の取得だけをして。プレビューは表示しないで。",
    ),
    (
        "要件サマリーのプレビュー",
        "「要件サマリー作成」機能で要件を取得し、出力して。要件サマリーの項目が足りないかを"
        "一度確認し、ない項目の値は適当に補完して",
    ),
    (
        "アイデアを出して",
        "このプロジェクトの機能や価値に関するアイデアをブレインストーミング的にアイデアを出力して",
    ),
    ("多角的に検証して", "多角的に検証して"),
    (
        "画面のイメージを出力して",
        "このプロジェクトの要件情報に基づいて画面のイメージを出力してみて。簡単に機能がわかるもので"
        "いいから忠実に要件を再現して。外部ファイルを参照しない単一のHTMLを、htmlのコードブロックで出力して。",
    ),
    (
        "利点と欠点をあげて",
        "このプロジェクトの要件情報の懸念点を批判的に洗い出し、利点と欠点を出力して。",
    ),
]


class Command(BaseCommand):
    help = "エージェントとテンプレの初期データを登録する（既存の行は上書きしない）"

    def handle(self, *args, **options):
        for spec in AGENTS:
            prompt = (SEED_DIR / f"{spec['key']}.md").read_text(encoding="utf-8")
            _, created = AgentConfig.objects.get_or_create(
                key=spec["key"], defaults={**spec, "role_prompt": prompt}
            )
            self.stdout.write(f"agent {spec['key']}: {'created' if created else 'kept'}")

        # テンプレは管理者が自由に編集・削除できるため、1件でもあれば初期登録済みとみなす
        if PromptTemplate.objects.exists():
            self.stdout.write("templates: kept")
            return
        PromptTemplate.objects.bulk_create(
            PromptTemplate(label=label, prompt=prompt, sort_order=index * 10)
            for index, (label, prompt) in enumerate(TEMPLATES, start=1)
        )
        self.stdout.write(f"templates: created {len(TEMPLATES)}")
