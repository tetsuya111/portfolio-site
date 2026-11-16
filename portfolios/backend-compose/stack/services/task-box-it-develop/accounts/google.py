"""GoogleのIDトークンの検証。テストではこの関数をモックする。"""

from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token


class InvalidGoogleToken(Exception):
    pass


def verify_google_credential(credential):
    """IDトークンの署名・aud・有効期限を検証し、クレームを返す。"""
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise InvalidGoogleToken("GOOGLE_OAUTH_CLIENT_ID が設定されていません")
    try:
        claims = id_token.verify_oauth2_token(
            credential, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
        )
    except ValueError as exc:
        raise InvalidGoogleToken(str(exc)) from exc
    if not claims.get("email") or not claims.get("email_verified"):
        raise InvalidGoogleToken("メールアドレスが確認されていません")
    return claims
