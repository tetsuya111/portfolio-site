"""TLS 検証に使う SSL コンテキスト。

certifi 同梱の CA ではなく OS の証明書ストアを使う。社内プロキシやウイルス対策ソフトの
HTTPS 検査で独自ルート CA が OS に登録されている環境でも、検証を無効にせず接続できる。
"""

import ssl
from functools import cache


@cache
def system_ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context()
