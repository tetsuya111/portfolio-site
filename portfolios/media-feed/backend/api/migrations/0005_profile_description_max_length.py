from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_article_articletag'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='description',
            field=models.TextField(blank=True, max_length=800),
        ),
    ]
