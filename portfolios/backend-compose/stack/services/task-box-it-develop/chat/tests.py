from datetime import timedelta

from django.utils import timezone

from agents.llm import LLMError
from agents.models import UsageRecord
from agents.testing import FakeLLMClient
from chat import services
from chat.models import Conversation, Message, PendingAgentCall
from config.testing import ApiTestCase, read_sse
from summaries.models import RequirementSummary

EXTRACTED = {"json": {"requirements_markdown": "# 要件\n予約管理", "completed_items": []}}
# 確定では、充足判定と要件の抽出を1回の呼び出しでまとめて行う
CHECKED_OK = {"json": {"complete": True, "missing": [], "requirements_markdown": "# 要件 予約管理"}}
CHECKED_MISSING = {
    "json": {"complete": False, "missing": ["セキュリティ", "予算のレンジ"], "requirements_markdown": ""}
}
EXTRACTED_PREVIEW = {
    "json": {"requirements_markdown": "# 要件\n予算: 10万円（仮）", "completed_items": ["予算のレンジ"]}
}
SUMMARY_OK = {
    "json": {"status": "ok", "title": "予約管理ツール", "body_markdown": "# 目的\n予約を楽にする",
             "missing_terms": [], "message": ""}
}
SUMMARY_ERROR = {
    "json": {"status": "error", "title": "", "body_markdown": "",
             "missing_terms": ["セキュリティ"], "message": "セキュリティの情報がない"}
}


class ChatTestCase(ApiTestCase):
    def send(self, content="予約管理のツールがほしい"):
        return self.client.post("/api/conversation/messages/", {"content": content})

    def talk(self):
        FakeLLMClient.queue.insert(0, "いいですね。どんな場面で使いますか？")
        read_sse(self.send())

    def conversation(self):
        return Conversation.objects.get(user=self.user)


class MessageTests(ChatTestCase):
    def test_reply_is_streamed_and_saved(self):
        FakeLLMClient.reset("いいですね。どんな場面で使いますか？")
        events = read_sse(self.send())
        self.assertEqual([e for e, _ in events], ["delta", "delta", "done"])
        self.assertEqual("".join(d["text"] for e, d in events if e == "delta"), events[-1][1]["message"]["content"])
        roles = [m["role"] for m in self.client.get("/api/conversation/").data["messages"]]
        self.assertEqual(roles, ["user", "assistant"])
        # 履歴を踏まえた応答になるよう、2通目では1通目の履歴が渡される
        FakeLLMClient.queue.append("なるほど")
        read_sse(self.send("美容室で使いたい"))
        self.assertEqual(len(FakeLLMClient.calls[1]["messages"]), 3)
        self.assertEqual(
            [t["name"] for t in FakeLLMClient.calls[1]["tools"]],
            ["call_market_estimate", "call_self_estimate", "call_summary"],
        )

    def test_tool_call_becomes_pending_dialog_without_running_agent(self):
        FakeLLMClient.reset({"tool": "call_market_estimate", "text": "見積もりますね"})
        events = read_sse(self.send("相場の見積もりをして。"))
        self.assertEqual(events[-1][0], "agent_call_request")
        self.assertEqual(events[-1][1]["agent_name"], "相場見積もり")
        self.assertEqual(len(FakeLLMClient.calls), 1)
        # tool use は保存されず、画面を開き直しても確認ダイアログが復元できる
        data = self.client.get("/api/conversation/").data
        self.assertEqual([m["role"] for m in data["messages"]], ["user"])
        self.assertEqual(data["pending_agent_call"]["agent_key"], "market_estimate")

    def test_llm_failure_keeps_user_message_and_releases_lock(self):
        FakeLLMClient.reset(LLMError("down", retryable=True))
        events = read_sse(self.send())
        self.assertEqual(events, [("error", {"code": "llm_failed", "message": services.LLM_FAILED_MESSAGE})])
        self.assertEqual(Message.objects.filter(role="user").count(), 1)
        self.assertIsNone(self.conversation().processing_started_at)

    def test_validation(self):
        self.assertEqual(self.send("  ").status_code, 400)
        response = self.send("あ" * 4001)
        self.assertEqual(response.data["code"], "message_too_long")
        self.assertEqual(len(FakeLLMClient.calls), 0)

    def test_users_only_see_their_own_conversation(self):
        FakeLLMClient.reset("はい")
        read_sse(self.send())
        self.assertEqual(self.as_user(self.other).get("/api/conversation/").data["messages"], [])


class LockTests(ChatTestCase):
    def test_busy_conversation_returns_409_and_recovers_after_timeout(self):
        conversation = services.get_conversation(self.user)
        Conversation.objects.filter(pk=conversation.pk).update(processing_started_at=timezone.now())
        response = self.send()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "conversation_busy")
        Conversation.objects.filter(pk=conversation.pk).update(
            processing_started_at=timezone.now() - timedelta(minutes=6)
        )
        FakeLLMClient.reset("はい")
        self.assertEqual(self.send().status_code, 200)


class AgentCallTests(ChatTestCase):
    def request_call(self, tool):
        FakeLLMClient.reset({"tool": tool})
        events = read_sse(self.send("お願い"))
        FakeLLMClient.calls.clear()
        return events[-1][1]["id"]

    def test_approve_estimate(self):
        call_id = self.request_call("call_self_estimate")
        FakeLLMClient.queue = [EXTRACTED_PREVIEW, SUMMARY_OK, "AI 1/7見積もり: 5万円"]
        response = self.client.post(f"/api/conversation/agent-calls/{call_id}/approve/")
        message = response.data["message"]
        self.assertEqual(message["kind"], "agent_result")
        self.assertTrue(message["metadata"]["is_estimate"])
        self.assertEqual(message["metadata"]["completed_items"], ["予算のレンジ"])
        # 見積もりエージェントには、要件サマリーだけが入力される（エージェント間はシステムが仲介）
        self.assertEqual(FakeLLMClient.calls[2]["messages"], [{"role": "user", "content": "# 目的\n予約を楽にする"}])
        # 内部処理の入力と出力は対話履歴に残らない
        contents = [m.content for m in Message.objects.all()]
        self.assertEqual(contents, ["お願い", "AI 1/7見積もり: 5万円"])

    def test_approve_summary_preview(self):
        call_id = self.request_call("call_summary")
        FakeLLMClient.queue = [EXTRACTED_PREVIEW, SUMMARY_OK]
        message = self.client.post(f"/api/conversation/agent-calls/{call_id}/approve/").data["message"]
        self.assertTrue(message["metadata"]["is_preview"])
        self.assertEqual(message["metadata"]["completed_items"], ["予算のレンジ"])
        self.assertIn("（仮）", FakeLLMClient.calls[1]["messages"][0]["content"])

    def test_decline_continues_chat_without_tools(self):
        call_id = self.request_call("call_market_estimate")
        FakeLLMClient.queue = ["わかりました。続けましょう"]
        response = self.client.post(f"/api/conversation/agent-calls/{call_id}/decline/")
        self.assertEqual(response.data["message"]["kind"], "chat")
        self.assertEqual(FakeLLMClient.calls[0]["tool_choice"], {"type": "none"})
        self.assertEqual(len(FakeLLMClient.calls), 1)

    def test_answered_or_foreign_call_is_rejected(self):
        call_id = self.request_call("call_market_estimate")
        FakeLLMClient.queue = ["はい"]
        self.client.post(f"/api/conversation/agent-calls/{call_id}/decline/")
        again = self.client.post(f"/api/conversation/agent-calls/{call_id}/approve/")
        self.assertEqual(again.status_code, 409)
        other = self.as_user(self.other).post(f"/api/conversation/agent-calls/{call_id}/approve/")
        self.assertEqual(other.status_code, 404)

    def test_failed_agent_does_not_stay_pending(self):
        call_id = self.request_call("call_market_estimate")
        FakeLLMClient.queue = [LLMError("down")]
        response = self.client.post(f"/api/conversation/agent-calls/{call_id}/approve/")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(PendingAgentCall.objects.get(pk=call_id).status, "approved")
        self.assertIsNone(self.client.get("/api/conversation/").data["pending_agent_call"])
        self.assertIsNone(self.conversation().processing_started_at)


class ActionTests(ChatTestCase):
    def test_actions_need_a_conversation_first(self):
        response = self.client.post("/api/conversation/actions/market-estimate/")
        self.assertEqual(response.data["code"], "conversation_empty")

    def test_estimate_buttons_run_without_dialog(self):
        self.talk()
        for path, key in (("market-estimate", "market_estimate"), ("self-estimate", "self_estimate")):
            FakeLLMClient.queue = [EXTRACTED_PREVIEW, SUMMARY_OK, "見積もり結果"]
            message = self.client.post(f"/api/conversation/actions/{path}/").data["message"]
            self.assertEqual(message["agent_key"], key)
            self.assertTrue(message["metadata"]["is_estimate"])
        self.assertFalse(PendingAgentCall.objects.exists())

    def test_summary_download(self):
        self.talk()
        FakeLLMClient.queue = [EXTRACTED_PREVIEW, SUMMARY_OK]
        data = self.client.post("/api/conversation/actions/summary-download/").data
        self.assertEqual(data["title"], "予約管理ツール")
        self.assertEqual(data["completed_items"], ["予算のレンジ"])
        self.assertEqual(Message.objects.count(), 2)

    def test_finalize_reports_missing_items(self):
        self.talk()
        # 不足があれば、サマリー作成エージェントは呼ばずに1回で打ち切る
        FakeLLMClient.queue = [CHECKED_MISSING]
        FakeLLMClient.calls = []
        data = self.client.post("/api/conversation/actions/finalize/").data
        self.assertEqual(data, {"complete": False, "missing": ["予算のレンジ", "セキュリティ"]})
        self.assertEqual(len(FakeLLMClient.calls), 1)
        self.assertFalse(RequirementSummary.objects.exists())

    def test_finalize_creates_single_draft(self):
        self.talk()
        for _ in range(2):
            FakeLLMClient.queue = [CHECKED_OK, SUMMARY_OK]
            FakeLLMClient.calls = []
            data = self.client.post("/api/conversation/actions/finalize/").data
        self.assertTrue(data["complete"])
        self.assertEqual(data["summary"]["title"], "予約管理ツール")
        draft = RequirementSummary.objects.get()
        self.assertIsNone(draft.submitted_at)
        # 充足判定と抽出で1回、サマリー作成で1回の計2回
        self.assertEqual(len(FakeLLMClient.calls), 2)
        # 確定用の抽出では補完をさせない
        self.assertIn("補完もしないで", FakeLLMClient.calls[0]["messages"][-1]["content"])

    def test_finalize_does_not_send_back_missing_terms_from_the_summary_agent(self):
        self.talk()
        FakeLLMClient.queue = [CHECKED_OK, SUMMARY_ERROR]
        response = self.client.post("/api/conversation/actions/finalize/")
        # 不足の判定は1回目に集約したため、確定では422（差し戻し）にしない
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data["code"], "llm_failed")
        self.assertFalse(RequirementSummary.objects.exists())

    def test_clear_keeps_submitted_summaries(self):
        self.talk()
        RequirementSummary.objects.create(
            user=self.user, title="t", body_markdown="b", submitted_at=timezone.now()
        )
        self.assertEqual(self.client.post("/api/conversation/clear/").status_code, 204)
        self.assertEqual(self.client.get("/api/conversation/").data["messages"], [])
        self.assertEqual(RequirementSummary.objects.count(), 1)


class RetentionTests(ChatTestCase):
    """保持期間（既定30日）を過ぎた対話履歴を消すバッチ。"""

    def age_messages(self, conversation, days):
        Message.objects.filter(conversation=conversation).update(
            created_at=timezone.now() - timedelta(days=days)
        )

    def purge(self, **kwargs):
        from chat.retention import purge_expired_conversations

        return purge_expired_conversations(**kwargs)

    def test_old_conversation_is_purged_and_recent_one_is_kept(self):
        self.talk()
        old = self.conversation()
        self.age_messages(old, 31)
        FakeLLMClient.queue.insert(0, "はい")
        read_sse(self.as_user(self.other).post("/api/conversation/messages/", {"content": "新しい相談"}))
        recent = Conversation.objects.get(user=self.other)

        result = self.purge()

        self.assertEqual(result["conversations"], 1)
        self.assertEqual(result["messages"], 2)
        self.assertEqual(old.messages.count(), 0)
        self.assertEqual(recent.messages.count(), 2)
        # 対話そのもの（1ユーザー1件の入れ物）は消さない
        self.assertEqual(Conversation.objects.count(), 2)

    def test_conversation_stays_while_it_is_used(self):
        self.talk()
        self.age_messages(self.conversation(), 31)
        # 新しいメッセージが1件でもあれば、起算点は最後のメッセージになる
        FakeLLMClient.queue.insert(0, "続きですね")
        read_sse(self.send("追加で相談したい"))
        self.assertEqual(self.purge()["conversations"], 0)
        self.assertEqual(self.conversation().messages.count(), 4)

    def test_pending_agent_calls_are_removed_but_summaries_and_usage_stay(self):
        self.talk()
        conversation = self.conversation()
        PendingAgentCall.objects.create(
            conversation=conversation, agent_key="market_estimate", agent_name="相場見積もり"
        )
        RequirementSummary.objects.create(
            user=self.user, title="t", body_markdown="b", submitted_at=timezone.now()
        )
        usage_before = UsageRecord.objects.count()
        self.age_messages(conversation, 40)

        self.purge()

        self.assertEqual(conversation.agent_calls.count(), 0)
        self.assertEqual(RequirementSummary.objects.count(), 1)
        self.assertEqual(UsageRecord.objects.count(), usage_before)

    def test_running_conversation_is_skipped(self):
        self.talk()
        conversation = self.conversation()
        self.age_messages(conversation, 31)
        Conversation.objects.filter(pk=conversation.pk).update(processing_started_at=timezone.now())
        self.assertEqual(self.purge()["conversations"], 0)
        self.assertEqual(conversation.messages.count(), 2)

    def test_empty_conversation_is_not_an_error(self):
        services.get_conversation(self.other)
        self.assertEqual(self.purge()["conversations"], 0)

    def test_dry_run_keeps_everything(self):
        self.talk()
        self.age_messages(self.conversation(), 31)
        result = self.purge(dry_run=True)
        self.assertEqual((result["conversations"], result["dry_run"]), (1, True))
        self.assertEqual(self.conversation().messages.count(), 2)

    def test_running_twice_changes_nothing(self):
        self.talk()
        self.age_messages(self.conversation(), 31)
        self.assertEqual(self.purge()["conversations"], 1)
        self.assertEqual(self.purge()["conversations"], 0)

    def test_command_reports_counts(self):
        from io import StringIO

        from django.core.management import call_command

        self.talk()
        self.age_messages(self.conversation(), 31)
        output = StringIO()
        call_command("purge_conversations", "--dry-run", stdout=output)
        self.assertIn("対話 1件", output.getvalue())
        self.assertEqual(self.conversation().messages.count(), 2)
        output = StringIO()
        call_command("purge_conversations", stdout=output)
        self.assertIn("を消しました", output.getvalue())
        self.assertEqual(self.conversation().messages.count(), 0)
