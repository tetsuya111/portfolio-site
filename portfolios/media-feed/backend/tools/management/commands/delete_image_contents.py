from django.core.management.base import BaseCommand

from api.models import Content


class Command(BaseCommand):
    help = "タイプが画像のコンテンツを全削除する"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="確認なしで削除する")

    def handle(self, *args, **options):
        count = Content.objects.filter(type=Content.TYPE_IMAGE).count()
        self.stdout.write(f"削除対象: {count} 件の画像コンテンツ")

        if count == 0:
            self.stdout.write("削除対象がありません")
            return

        if not options["force"]:
            confirm = input("削除しますか？ [y/N]: ")
            if confirm.lower() != "y":
                self.stdout.write("キャンセルしました")
                return

        Content.objects.filter(type=Content.TYPE_IMAGE).delete()
        self.stdout.write(self.style.SUCCESS(f"{count} 件の画像コンテンツを削除しました"))
