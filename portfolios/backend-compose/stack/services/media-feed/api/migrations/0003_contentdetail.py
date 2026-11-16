import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_content_source_url'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContentDetail',
            fields=[
                ('content', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    primary_key=True,
                    related_name='detail',
                    serialize=False,
                    to='api.content',
                )),
                ('series_id', models.CharField(default='-1', max_length=100)),
                ('series_number', models.IntegerField(default=-1)),
            ],
            options={'verbose_name': 'コンテンツ詳細'},
        ),
    ]
