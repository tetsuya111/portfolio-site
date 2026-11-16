from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_userdetail'),
    ]

    operations = [
        migrations.CreateModel(
            name='Inquiry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('title', models.CharField(max_length=200)),
                ('email', models.EmailField(max_length=254)),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'お問い合わせ',
                'ordering': ['-created_at'],
            },
        ),
    ]
