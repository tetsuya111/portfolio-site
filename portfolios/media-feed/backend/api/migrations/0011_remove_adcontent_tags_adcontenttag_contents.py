from django.db import migrations, models


def _fix_adcontent_table(apps, schema_editor):
    """
    実際のDBは 0010 の初期FK版で適用済み（tag_id カラムあり、width/height/M2M なし）。
    ファイルを書き換えたため仮想状態とズレているので、ここで実DBを正しい状態に揃える。
    """
    cursor = schema_editor.connection.cursor()

    # 現在のカラム一覧を取得
    cursor.execute("PRAGMA table_info(api_adcontent)")
    columns = {row[1] for row in cursor.fetchall()}

    if "tag_id" in columns or "width" not in columns:
        # テーブルを再作成して tag_id を除去し、width/height を追加
        cursor.execute("""
            CREATE TABLE api_adcontent_new (
                "id"     integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                "html"   text    NOT NULL,
                "width"  integer NULL,
                "height" integer NULL
            )
        """)
        cursor.execute(
            "INSERT INTO api_adcontent_new (id, html) SELECT id, html FROM api_adcontent"
        )
        cursor.execute("DROP TABLE api_adcontent")
        cursor.execute("ALTER TABLE api_adcontent_new RENAME TO api_adcontent")

    # M2M 中間テーブルを作成（adcontenttag.contents → adcontent）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "api_adcontenttag_contents" (
            "id"              integer      NOT NULL PRIMARY KEY AUTOINCREMENT,
            "adcontenttag_id" varchar(100) NOT NULL
                REFERENCES "api_adcontenttag" ("name") DEFERRABLE INITIALLY DEFERRED,
            "adcontent_id"    bigint       NOT NULL
                REFERENCES "api_adcontent" ("id") DEFERRABLE INITIALLY DEFERRED,
            UNIQUE ("adcontenttag_id", "adcontent_id")
        )
    """)


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_adcontent'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # Django の仮想状態を更新
            state_operations=[
                migrations.RemoveField(
                    model_name='adcontent',
                    name='tags',
                ),
                migrations.AddField(
                    model_name='adcontenttag',
                    name='contents',
                    field=models.ManyToManyField(
                        blank=True,
                        related_name='tags',
                        to='api.adcontent',
                    ),
                ),
            ],
            # 実DBの操作（実態に合わせた手動処理）
            database_operations=[
                migrations.RunPython(_fix_adcontent_table, migrations.RunPython.noop),
            ],
        ),
    ]
