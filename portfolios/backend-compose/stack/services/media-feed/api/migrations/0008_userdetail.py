import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def create_user_details(apps, schema_editor):
    User = apps.get_model('api', 'User')
    UserDetail = apps.get_model('api', 'UserDetail')
    for user in User.objects.all():
        is_admin = user.is_staff or user.is_superuser or user.username == 'admin'
        UserDetail.objects.get_or_create(
            user=user,
            defaults={
                'is_affiliate': is_admin,
                'is_uploader': is_admin,
                'is_author': is_admin,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0007_clickcount'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserDetail',
            fields=[
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    primary_key=True,
                    related_name='user_detail',
                    serialize=False,
                    to=settings.AUTH_USER_MODEL,
                )),
                ('is_affiliate', models.BooleanField(default=False)),
                ('is_uploader', models.BooleanField(default=False)),
                ('is_author', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'ユーザー詳細',
            },
        ),
        migrations.RunPython(create_user_details, migrations.RunPython.noop),
    ]
