"""FastAPI のアプリ。Webhookは署名を検証してすぐに200を返し、処理はジョブキューに渡す。"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import text as sql_text
from sqlalchemy.exc import IntegrityError

from . import messages as msg
from . import public_url
from .config import get_settings
from .db import session_scope
from .features import registration, router
from .line.client import LineApiError, get_client, verify_signature
from .models import ProcessedEvent
from .startup import configure_public_url, setup_logging
from .tasks import dispatch

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 公開URLの解決とLINEのWebhook設定は、起動時に1回だけ行う（失敗しても起動を止めない）
    setup_logging()
    configure_public_url()
    yield


app = FastAPI(title="タスク百葉箱 LINE BOT", lifespan=lifespan)


@app.get("/healthz")
def healthz() -> JSONResponse:
    checks = {"db": False, "redis": False}
    try:
        with session_scope() as session:
            session.execute(sql_text("SELECT 1"))
        checks["db"] = True
    except Exception as exc:
        logger.warning("DBへの疎通に失敗: %s", type(exc).__name__)
    try:
        from redis import Redis

        Redis.from_url(get_settings().redis_url).ping()
        checks["redis"] = True
    except Exception as exc:
        logger.warning("Redis（Celeryのブローカー）への疎通に失敗: %s", type(exc).__name__)
    ok = all(checks.values())
    # 公開URLは ok の判定に含めない（無くてもアプリ自体は健全）。貼り忘れに気づくために出す
    body = {
        "ok": ok, **checks,
        "public_url": public_url.current(),
        "ngrok": get_settings().use_ngrok,
    }
    return JSONResponse(body, status_code=200 if ok else 503)


def _forget(event_id: str) -> None:
    """処理を渡せなかったイベントの記録を消す（LINEの再送で拾えるようにする）。"""
    with session_scope() as session:
        event = session.get(ProcessedEvent, event_id)
        if event is not None:
            session.delete(event)


def _remember(event_id: str) -> bool:
    """未処理なら True。INSERTの主キー違反で重複を弾く（SELECT→INSERTにしない）。"""
    try:
        with session_scope() as session:
            session.add(ProcessedEvent(webhook_event_id=event_id))
    except IntegrityError:
        logger.info("重複したイベントのため処理しません: event=%s", event_id)
        return False
    return True


@app.post("/webhook")
async def webhook(request: Request, x_line_signature: str | None = Header(default=None)):
    body = await request.body()
    if not verify_signature(body, x_line_signature):
        logger.warning("署名の検証に失敗しました")
        return Response(status_code=400)
    try:
        payload = await request.json()
    except ValueError:
        return Response(status_code=400)

    for event in router.extract_events(payload):
        if not _remember(event["event_id"]):
            continue
        if router.is_dialogue(event) and event.get("reply_token"):
            # 時間がかかるため、先に待機メッセージを返す（replyは通数を消費しない）
            try:
                get_client().reply(event["reply_token"], msg.WAITING)
            except LineApiError as exc:
                logger.warning("待機メッセージの送信に失敗: %s", exc)
            event = {**event, "reply_token": None}
        try:
            dispatch(event)
        except Exception as exc:
            # ブローカーへ渡せないまま「処理済み」にすると、そのイベントは二度と処理されない
            logger.warning("タスクの送信に失敗: %s", type(exc).__name__)
            _forget(event["event_id"])
            return Response(status_code=500)
    # 個々の処理の結果は応答に含めず、常に200を返す
    return Response(status_code=200)


@app.get("/liff", response_class=HTMLResponse)
def liff_page() -> HTMLResponse:
    """LINE内で開く登録フォーム。userId は送らせず、IDトークンをサーバーで検証する。"""
    liff_id = get_settings().liff_id
    if not liff_id:
        return HTMLResponse("<p>準備中です。</p>", status_code=404)
    return HTMLResponse(
        """<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ユーザー情報の登録</title>
<script src="https://static.line-scdn.net/liff/edge/2/sdk.js"></script>
<style>body{font-family:sans-serif;margin:24px;line-height:1.7}
label{display:block;margin-top:16px}input{width:100%;padding:8px;font-size:16px}
button{margin-top:24px;padding:12px 24px;font-size:16px}p#result{margin-top:16px}</style>
</head><body>
<h1>ユーザー情報の登録</h1>
<label>お名前<input id="name" maxlength="50"></label>
<label>メールアドレス<input id="email" type="email" maxlength="254"></label>
<button id="send">登録する</button>
<p id="result"></p>
<script>
  liff.init({ liffId: "__LIFF_ID__" });
  document.getElementById("send").onclick = async () => {
    const result = document.getElementById("result");
    result.textContent = "送信しています…";
    const response = await fetch("/liff/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        id_token: liff.getIDToken(),
        name: document.getElementById("name").value,
        email: document.getElementById("email").value,
      }),
    });
    const data = await response.json();
    result.textContent = data.message;
    if (response.ok) setTimeout(() => liff.closeWindow(), 1500);
  };
</script>
</body></html>""".replace("__LIFF_ID__", liff_id)
    )


@app.post("/liff/register")
async def liff_register(request: Request) -> JSONResponse:
    payload = await request.json()
    id_token = payload.get("id_token")
    if not id_token:
        return JSONResponse({"message": "もう一度お試しください。"}, status_code=400)
    try:
        # クライアントから送られた userId は使わず、検証の結果を使う
        line_user_id = get_client().verify_id_token(id_token)
    except LineApiError:
        return JSONResponse({"message": "もう一度お試しください。"}, status_code=401)
    try:
        name, email = registration.validate(payload.get("name", ""), payload.get("email", ""))
    except registration.ValidationError as exc:
        return JSONResponse({"message": str(exc)}, status_code=400)
    with session_scope() as session:
        registration.register(session, line_user_id, name, email)
    return JSONResponse({"message": msg.REGISTERED})
