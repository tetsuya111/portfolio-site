import django.db.models.deletion
from django.db import migrations, models


def migrate_series_data(apps, schema_editor):
    ContentDetail = apps.get_model('api', 'ContentDetail')
    Series = apps.get_model('api', 'Series')
    for detail in ContentDetail.objects.all():
        sid = detail.series_id_old
        if sid and sid != '-1':
            series, _ = Series.objects.get_or_create(series_id=sid)
            detail.series = series
            detail.save(update_fields=['series'])


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_profile_description_max_length'),
    ]

    operations = [
        # Series・SeriesQueueItem 作成
        migrations.CreateModel(
            name='Series',
            fields=[
                ('series_id', models.CharField(max_length=100, primary_key=True, serialize=False)),
                ('weight', models.FloatField(default=10)),
            ],
            options={'verbose_name': 'シリーズ'},
        ),
        migrations.CreateModel(
            name='SeriesQueueItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('series_id', models.CharField(max_length=100)),
            ],
            options={'verbose_name': 'シリーズキューアイテム'},
        ),
        # 旧 series_id を一時的にリネームして FK の series_id カラムとの衝突を回避
        migrations.RenameField(
            model_name='contentdetail',
            old_name='series_id',
            new_name='series_id_old',
        ),
        # 新 series FK を追加（DB カラム名 = series_id）
        migrations.AddField(
            model_name='contentdetail',
            name='series',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='content_details',
                to='api.series',
            ),
        ),
        # データ移行：旧 series_id_old → Series オブジェクト → series FK
        migrations.RunPython(migrate_series_data, migrations.RunPython.noop),
        # 旧カラム削除
        migrations.RemoveField(
            model_name='contentdetail',
            name='series_id_old',
        ),
    ]
