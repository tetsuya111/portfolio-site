from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_contentdetail'),
    ]

    operations = [
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=500)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='articles', to=settings.AUTH_USER_MODEL)),
                ('contents', models.ManyToManyField(blank=True, related_name='articles', to='api.content')),
                ('thumbnail', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='thumbnail_of', to='api.content')),
            ],
            options={
                'verbose_name': '記事',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ArticleTag',
            fields=[
                ('name', models.CharField(max_length=100, primary_key=True, serialize=False)),
                ('articles', models.ManyToManyField(blank=True, related_name='article_tags', to='api.article')),
            ],
            options={
                'verbose_name': '記事タグ',
            },
        ),
    ]
