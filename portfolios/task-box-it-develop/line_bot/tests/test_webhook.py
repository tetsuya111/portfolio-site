"""Webhookの受信（署名・冪等性・対象外イベント）と、機能の振り分け。"""

from app import messages as msg
from app.db import session_scope
from app.models import ContractStatus, ProcessedEvent, User

from .conftest import USER_ID, make_user, post_webhook, postback_event, sign, text_event


class TestSignature:
    def test_valid_signature_is_accepted(self, api):
        assert post_webhook(api, text_event("こんにちは")).status_code == 200

    def test_tampered_body_is_rejected(self, api, queue):
        import json

        body = json.dumps(text_event("こんにちは")).encode()
        signature = sign(body)
        # 署名を計算したあとに本文を変える（JSONとしては読めるまま）
        response = api.post(
            "/webhook",
            content=body + b" ",
            headers={"X-Line-Signature": signature, "Content-Type": "application/json"},
        )
        assert response.status_code == 400
        assert queue.calls == []

    def test_missing_signature_is_rejected(self, api, queue):
        assert post_webhook(api, text_event("やあ"), signature=None).status_code == 400
        assert queue.calls == []


class TestIdempotency:
    def test_same_event_is_processed_once(self, api, queue, line):
        payload = text_event("【ユーザー情報の登録】\n名前: 山田\nメールアドレス: y@example.com")
        assert post_webhook(api, payload).status_code == 200
        assert post_webhook(api, payload).status_code == 200
        assert len(queue.calls) == 1
        assert len(line.replies) == 1
        with session_scope() as session:
            assert session.query(ProcessedEvent).count() == 1


class TestBrokerFailure:
    def test_failure_to_dispatch_returns_500_and_forgets_the_event(self, api, monkeypatch):
        """ブローカーへ渡せないときに「処理済み」を残すと、そのイベントは二度と処理されない。"""
        from app import main

        def boom(event):
            raise RuntimeError("broker down")

        monkeypatch.setattr(main, "dispatch", boom)
        assert post_webhook(api, text_event("こんにちは")).status_code == 500
        with session_scope() as session:
            assert session.query(ProcessedEvent).count() == 0


class TestIgnoredEvents:
    def test_sticker_and_follow_are_ignored(self, api, queue, line):
        payload = {"events": [
            {"type": "message", "webhookEventId": "e1", "replyToken": "r",
             "source": {"userId": USER_ID}, "message": {"type": "sticker"}},
            {"type": "follow", "webhookEventId": "e2", "source": {"userId": USER_ID}},
            {"type": "join", "webhookEventId": "e3", "source": {"type": "group", "groupId": "G1"}},
        ]}
        assert post_webhook(api, payload).status_code == 200
        assert queue.calls == []
        assert line.replies == []

    def test_unfollow_keeps_the_user(self, api):
        make_user()
        payload = {"events": [
            {"type": "unfollow", "webhookEventId": "e-unfollow", "source": {"userId": USER_ID}}
        ]}
        post_webhook(api, payload)
        with session_scope() as session:
            assert session.get(User, USER_ID) is not None


class TestRouting:
    def test_unregistered_text_is_guided_without_llm(self, api, line, queue, llm):
        post_webhook(api, text_event("ツールを作ってほしい"))
        assert msg.NOT_CONTRACTED in line.replies[0][1]
        assert msg.NEED_REGISTRATION in line.replies[0][1]
        assert llm.calls == []

    def test_non_contracted_text_does_not_call_llm(self, api, line, llm):
        make_user(contracted=False)
        post_webhook(api, text_event("見積もりして"))
        assert line.replies[0][1] == msg.NOT_CONTRACTED
        assert llm.calls == []
        assert line.pushes == []

    def test_postback_actions(self, api, line, monkeypatch):
        post_webhook(api, postback_event("action=meeting", event_id="p1"))
        assert line.replies[-1][1] == msg.UNDER_CONSTRUCTION

        post_webhook(api, postback_event("action=contract", event_id="p2"))
        assert line.replies[-1][1] == msg.UNDER_CONSTRUCTION  # URL未設定のあいだ

        monkeypatch.setenv("CONTRACT_PAGE_URL", "https://example.com/contract")
        from app import config

        config.reset_settings()
        post_webhook(api, postback_event("action=contract", event_id="p3"))
        assert "https://example.com/contract" in line.replies[-1][1]

        post_webhook(api, postback_event("action=register", event_id="p4"))
        assert "【ユーザー情報の登録】" in line.replies[-1][1]

    def test_unknown_postback_is_ignored(self, api, line):
        post_webhook(api, postback_event("action=unknown"))
        assert line.replies == []

    def test_quick_reply_is_attached_to_every_message(self):
        from app.line.client import text_message

        message = text_message("こんにちは")
        labels = [item["action"]["label"] for item in message["quickReply"]["items"]]
        assert labels == ["ユーザー情報の登録", "面談予定日の調整", "契約する"]


class TestRegistration:
    FORMAT = "【ユーザー情報の登録】\n名前: 山田 太郎\nメールアドレス: taro@example.com"

    def test_registers_from_text(self, api, line):
        post_webhook(api, text_event(self.FORMAT))
        assert line.replies[0][1] == msg.REGISTERED
        with session_scope() as session:
            user = session.get(User, USER_ID)
            assert (user.name, user.email) == ("山田 太郎", "taro@example.com")
            assert user.contract_status == ContractStatus.NONE

    def test_invalid_email_is_reported_with_an_example(self, api, line):
        post_webhook(api, text_event("【ユーザー情報の登録】\n名前: 山田\nメールアドレス: これ"))
        reply = line.replies[0][1]
        assert "メールアドレスの形式" in reply
        assert "taro@example.com" in reply
        with session_scope() as session:
            assert session.get(User, USER_ID) is None

    def test_missing_label_is_reported(self, api, line):
        post_webhook(api, text_event("【ユーザー情報の登録】\n名前: 山田"))
        assert "形式が違います" in line.replies[0][1]

    def test_re_registration_overwrites_but_keeps_contract(self, api, line):
        make_user(contracted=True)
        post_webhook(api, text_event(self.FORMAT))
        with session_scope() as session:
            user = session.get(User, USER_ID)
            assert user.name == "山田 太郎"
            assert user.contract_status == ContractStatus.ACTIVE

    def test_user_id_comes_from_the_signed_event(self, api, line):
        """本文に他人のIDを書いても、署名を検証したイベントの userId が使われる。"""
        payload = text_event(self.FORMAT + "\nuserId: U-someone-else")
        post_webhook(api, payload)
        with session_scope() as session:
            assert session.get(User, USER_ID) is not None
            assert session.get(User, "U-someone-else") is None


class TestLiffRegister:
    def test_uses_verified_sub_instead_of_the_posted_user_id(self, api, line):
        line.id_token_sub = "U-verified"
        response = api.post("/liff/register", json={
            "id_token": "token", "name": "山田", "email": "y@example.com",
            "userId": "U-spoofed",
        })
        assert response.status_code == 200
        with session_scope() as session:
            assert session.get(User, "U-verified") is not None
            assert session.get(User, "U-spoofed") is None

    def test_validation_error_is_returned(self, api, line):
        response = api.post("/liff/register", json={
            "id_token": "token", "name": "", "email": "y@example.com",
        })
        assert response.status_code == 400
        assert "お名前" in response.json()["message"]

    def test_liff_page_is_hidden_until_configured(self, api):
        assert api.get("/liff").status_code == 404
