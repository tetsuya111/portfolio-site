from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_inquiry'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdContentTag',
            fields=[
                ('name', models.CharField(max_length=100, primary_key=True, serialize=False)),
            ],
            options={
                'verbose_name': '広告コンテンツタグ',
            },
        ),
        migrations.CreateModel(
            name='AdContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('html', models.TextField()),
                ('width', models.IntegerField(blank=True, null=True)),
                ('height', models.IntegerField(blank=True, null=True)),
                ('tags', models.ManyToManyField(
                    blank=True,
                    related_name='ad_contents',
                    to='api.adcontenttag',
                )),
            ],
            options={
                'verbose_name': '広告コンテンツ',
            },
        ),
    ]
