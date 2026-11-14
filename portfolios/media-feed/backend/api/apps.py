from django.apps import AppConfig
from django.db.backends.signals import connection_created


def _configure_sqlite(sender, connection, **kwargs):
    """SQLite を WAL モードにする。

    既定のロールバックジャーナルでは書き込み中に読み取りがブロックされ、
    収集バッチが走っている間フィード一覧APIが詰まる。WAL なら読み取りは待たされない。
    """
    if connection.vendor != 'sqlite':
        return
    with connection.cursor() as cursor:
        cursor.execute('PRAGMA journal_mode=WAL;')
        cursor.execute('PRAGMA synchronous=NORMAL;')
        cursor.execute('PRAGMA busy_timeout=5000;')


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        connection_created.connect(
            _configure_sqlite, dispatch_uid='api.configure_sqlite'
        )
