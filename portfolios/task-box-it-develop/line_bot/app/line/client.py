"""LINE Messaging API のクライアントと、署名の検証。

テストでは FakeLineClient に差し替え、実際のAPIを呼ばない。
"""

import base64
import hashlib
import hmac
import logging
import time
import uuid

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)

REPLY_URL = "https://api.line.me/v2/bot/message/reply"
PUSH_URL = "https://api.line.me/v2/bot/message/push"
VERIFY_URL = "https://api.line.me/oauth2/v2.1/verify"
WEBHOOK_ENDPOINT_URL = "https://api.line.me/v2/bot/channel/webhook/endpoint"
WEBHOOK_TEST_URL = "https://api.line.me/v2/bot/channel/webhook/test"

MAX_ATTEMPTS = 3


class LineApiError(Exception):
    pass


class Blocked(LineApiError):
    """ブロック済みのユーザーへの送信（403）。再試行しない。"""


def verify_signature(body: bytes, signature: str | None) -> bool:
    """生のボディで検証する。JSONにし直した文字列では一致しない。"""
    secret = get_settings().channel_secret
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def quick_reply_items() -> list[dict]:
    """すべての返信に付ける、機能のクイックリプライ。"""
    return [
        {"type": "action", "action": {"type": "postback", "label": label, "data": f"action={key}",
                                      "displayText": label}}
        for key, label in (
            ("register", "ユーザー情報の登録"),
            ("meeting", "面談予定日の調整"),
            ("contract", "契約する"),
        )
    ]


def text_message(text: str, quick_reply: bool = True) -> dict:
    message: dict = {"type": "text", "text": text}
    if quick_reply:
        message["quickReply"] = {"items": quick_reply_items()}
    return message


class LineClient:
    """Messaging API の薄いクライアント。"""

    def __init__(self, access_token: str | None = None, timeout: float = 10.0):
        self.access_token = access_token or get_settings().channel_access_token
        self.timeout = timeout

    def _headers(self, retry_key: str | None = None) -> dict:
        if not self.access_token:
            raise LineApiError("LINE_CHANNEL_ACCESS_TOKEN が設定されていません")
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        if retry_key:
            headers["X-Line-Retry-Key"] = retry_key
        return headers

    def reply(self, reply_token: str, text: str, quick_reply: bool = True) -> None:
        payload = {"replyToken": reply_token, "messages": [text_message(text, quick_reply)]}
        self._post(REPLY_URL, payload, retry_key=None)

    def push(self, line_user_id: str, text: str, quick_reply: bool = True,
             retry_key: str | None = None) -> None:
        # 再試行でも同じキーを使い、二重送信を防ぐ
        retry_key = retry_key or str(uuid.uuid4())
        payload = {"to": line_user_id, "messages": [text_message(text, quick_reply)]}
        self._post(PUSH_URL, payload, retry_key=retry_key)

    def _post(self, url: str, payload: dict, retry_key: str | None) -> None:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = httpx.post(
                    url, json=payload, headers=self._headers(retry_key), timeout=self.timeout
                )
            except httpx.RequestError as exc:
                if attempt == MAX_ATTEMPTS:
                    raise LineApiError(f"送信に失敗しました: {type(exc).__name__}") from exc
                time.sleep(2 ** attempt)
                continue
            if response.status_code < 300:
                return
            if response.status_code == 403:
                # ブロック済み。記録するだけで再試行しない
                raise Blocked("ブロック済みのユーザーには送信できません")
            if response.status_code == 429:
                wait = float(response.headers.get("Retry-After", 2 ** attempt))
                if attempt == MAX_ATTEMPTS:
                    raise LineApiError("レート制限")
                time.sleep(wait)
                continue
            if response.status_code >= 500:
                if attempt == MAX_ATTEMPTS:
                    raise LineApiError(f"LINE APIのエラー: {response.status_code}")
                time.sleep(2 ** attempt)
                continue
            raise LineApiError(f"LINE APIのエラー: {response.status_code}")

    def _call(self, method: str, url: str, **kwargs) -> httpx.Response:
        """httpx の例外も LineApiError にそろえる（呼び出し元が1種類だけ捕まえれば済む）。"""
        try:
            return httpx.request(
                method, url, headers=self._headers(), timeout=self.timeout, **kwargs
            )
        except httpx.HTTPError as exc:
            raise LineApiError(f"通信に失敗しました: {type(exc).__name__}") from exc

    def get_webhook_endpoint(self) -> str:
        """チャネルに設定されているWebhookのURL。"""
        response = self._call("GET", WEBHOOK_ENDPOINT_URL)
        if response.status_code != 200:
            raise LineApiError(f"取得に失敗しました: {response.status_code}")
        return response.json().get("endpoint", "")

    def set_webhook_endpoint(self, url: str) -> None:
        response = self._call("PUT", WEBHOOK_ENDPOINT_URL, json={"endpoint": url})
        if response.status_code >= 300:
            raise LineApiError(f"更新に失敗しました: {response.status_code}")

    def test_webhook_endpoint(self) -> bool:
        """LINEから設定済みのURLへテストのリクエストを送らせる。"""
        response = self._call("POST", WEBHOOK_TEST_URL, json={})
        if response.status_code != 200:
            raise LineApiError(f"疎通確認に失敗しました: {response.status_code}")
        return bool(response.json().get("success"))

    def verify_id_token(self, id_token: str) -> str:
        """LIFFのIDトークンを検証し、userId（sub）を返す。"""
        settings = get_settings()
        if not settings.liff_id:
            raise LineApiError("LIFF_ID が設定されていません")
        response = httpx.post(
            VERIFY_URL,
            data={"id_token": id_token, "client_id": settings.liff_id.split("-")[0]},
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise LineApiError("IDトークンの検証に失敗しました")
        sub = response.json().get("sub")
        if not sub:
            raise LineApiError("IDトークンにユーザーIDが含まれていません")
        return sub


class FakeLineClient(LineClient):
    """テスト用。送信内容を記録するだけで、実際のAPIを呼ばない。"""

    def __init__(self, *args, **kwargs):
        self.replies: list[tuple[str, str]] = []
        self.pushes: list[tuple[str, str, str | None]] = []
        self.id_token_sub = "U-liff"
        # Webhookエンドポイントの操作の記録
        self.webhook_endpoint = ""
        self.endpoint_updates: list[str] = []
        self.endpoint_tests = 0
        self.test_result = True

    def reply(self, reply_token: str, text: str, quick_reply: bool = True) -> None:
        self.replies.append((reply_token, text))

    def push(self, line_user_id: str, text: str, quick_reply: bool = True,
             retry_key: str | None = None) -> None:
        self.pushes.append((line_user_id, text, retry_key))

    def get_webhook_endpoint(self) -> str:
        return self.webhook_endpoint

    def set_webhook_endpoint(self, url: str) -> None:
        self.webhook_endpoint = url
        self.endpoint_updates.append(url)

    def test_webhook_endpoint(self) -> bool:
        self.endpoint_tests += 1
        return self.test_result

    def verify_id_token(self, id_token: str) -> str:
        return self.id_token_sub


_client: LineClient | None = None


def get_client() -> LineClient:
    global _client
    if _client is None:
        _client = LineClient()
    return _client


def set_client(client: LineClient | None) -> None:
    """テストで差し替える。"""
    global _client
    _client = client
