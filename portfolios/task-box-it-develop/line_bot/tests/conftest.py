"""テスト共通の土台。LINE Messaging API とLLMは必ず偽のクライアントに差し替える。"""

import base64
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

SECRET = "test-channel-secret"
USER_ID = "U-tester"


@pytest.fixture(autouse=True)
def environment(tmp_path, monkeypatch):
    monkeypatch.setenv("LINE_CHANNEL_SECRET", SECRET)
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.sqlite3'}")
    monkeypatch.setenv("LLM_CLIENT_CLASS", "app.agents.llm.FakeLLMClient")
    # 既定は「プロンプト未作成」の状態にする（仮の応答）
    monkeypatch.setenv("DIALOGUE_PROMPT_FILE", str(tmp_path / "dialogue.md"))
    monkeypatch.setenv("LIFF_ID", "")
    # 公開URL。ローカルの .env（USE_NGROK=true など）に左右されないよう固定する
    monkeypatch.setenv("USE_NGROK", "false")
    monkeypatch.setenv("PUBLIC_BASE_URL", "")
    monkeypatch.setenv("NGROK_API_URL", "http://127.0.0.1:4040/api/tunnels")
    monkeypatch.setenv("NGROK_TUNNEL_NAME", "")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("CONTRACT_PAGE_URL", "")
    monkeypatch.setenv("HEARING_SITE_URL", "")
    monkeypatch.setenv("DAILY_LLM_CALL_LIMIT", "30")
    monkeypatch.setenv("HISTORY_MAX_TURNS", "10")

    from app import config, db
    from app.models import Base

    config.reset_settings()
    db.reset_engine()
    Base.metadata.create_all(db.get_engine())
    yield
    db.reset_engine()
    config.reset_settings()


@pytest.fixture
def line():
    from app.line.client import FakeLineClient, set_client

    client = FakeLineClient()
    set_client(client)
    yield client
    set_client(None)


@pytest.fixture
def queue(monkeypatch):
    """Celeryのブローカーを使わず、その場で処理する差し替え。送ったイベントを記録する。"""
    from app import main
    from app.features import router

    class Dispatcher:
        def __init__(self):
            self.calls: list[dict] = []

        def __call__(self, event: dict) -> None:
            self.calls.append(event)
            router.handle_event(event)

    dispatcher = Dispatcher()
    monkeypatch.setattr(main, "dispatch", dispatcher)
    return dispatcher


@pytest.fixture
def llm():
    from app.agents.llm import FakeLLMClient

    FakeLLMClient.reset()
    return FakeLLMClient


@pytest.fixture
def api(line, queue):
    from app.main import app

    return TestClient(app)


def sign(body: bytes, secret: str = SECRET) -> str:
    return base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()


def post_webhook(api, payload: dict, signature: str | None = "valid"):
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if signature == "valid":
        headers["X-Line-Signature"] = sign(body)
    elif signature is not None:
        headers["X-Line-Signature"] = signature
    return api.post("/webhook", content=body, headers=headers)


def text_event(text: str, user_id: str = USER_ID, event_id: str = "evt-1", reply_token="reply-1"):
    return {
        "events": [{
            "type": "message", "webhookEventId": event_id, "replyToken": reply_token,
            "source": {"type": "user", "userId": user_id},
            "message": {"type": "text", "text": text},
        }]
    }


def postback_event(data: str, user_id: str = USER_ID, event_id: str = "evt-p"):
    return {
        "events": [{
            "type": "postback", "webhookEventId": event_id, "replyToken": "reply-p",
            "source": {"type": "user", "userId": user_id},
            "postback": {"data": data},
        }]
    }


def make_user(line_user_id: str = USER_ID, contracted: bool = False, **kwargs):
    from app.db import session_scope
    from app.models import ContractStatus, User

    with session_scope() as session:
        session.add(User(
            line_user_id=line_user_id,
            name=kwargs.get("name", "依頼 太郎"),
            email=kwargs.get("email", "irai@example.com"),
            contract_status=ContractStatus.ACTIVE if contracted else ContractStatus.NONE,
        ))
