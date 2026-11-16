from unittest import mock

from django.core import mail
from django.utils import timezone

from config.testing import ApiTestCase
from summaries.models import RequirementSummary
from summaries.services import clean_title, create_draft


class SubmitTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.draft = create_draft(self.user, "予約管理ツール", "# 目的\n予約を楽にする")

    def submit(self, client=None):
        return (client or self.client).post(f"/api/summaries/{self.draft.id}/submit/")

    def test_submit_saves_and_sends_mail_once(self):
        first, second = self.submit(), self.submit()
        for response in (first, second):
            self.assertEqual(response.data, {"submitted": True, "notice": "管理者からのメールをお待ちください"})
        self.draft.refresh_from_db()
        self.assertIsNotNone(self.draft.submitted_at)
        self.assertEqual(self.draft.mail_status, "sent")
        self.assertEqual(self.draft.handling_status, "new")
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["owner@example.com"])
        self.assertEqual(message.subject, "【タスク百葉箱】要件サマリー「予約管理ツール」")
        self.assertEqual(message.body, "依頼 太郎さんから要件サマリーが届きました")
        name, content, mimetype = message.attachments[0]
        self.assertTrue(name.endswith(".md"))
        self.assertEqual(content, "# 目的\n予約を楽にする")

    def test_mail_failure_keeps_summary(self):
        with mock.patch("summaries.services.send_summary_mail", side_effect=OSError("smtp down")):
            response = self.submit()
        self.assertEqual(response.status_code, 200)
        self.draft.refresh_from_db()
        self.assertIsNotNone(self.draft.submitted_at)
        self.assertEqual(self.draft.mail_status, "failed")
        self.assertIn("smtp down", self.draft.mail_error)

    def test_other_user_cannot_submit(self):
        self.assertEqual(self.submit(self.as_user(self.other)).status_code, 404)
        self.draft.refresh_from_db()
        self.assertIsNone(self.draft.submitted_at)

    def test_title_is_sanitized(self):
        self.assertEqual(clean_title("予約\r\nBcc: x@example.com\x00ツール"), "予約 Bcc: x@example.com ツール")
        self.assertEqual(len(clean_title("あ" * 300)), 100)
        self.assertEqual(clean_title(" \n "), "無題の要件サマリー")

    def test_new_draft_replaces_old_draft_only(self):
        self.submit()
        create_draft(self.user, "a", "a")
        create_draft(self.user, "b", "b")
        self.assertEqual(RequirementSummary.objects.filter(submitted_at__isnull=True).count(), 1)
        self.assertEqual(RequirementSummary.objects.count(), 2)


class AdminSummaryTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.admin_client = self.as_user(self.admin)
        now = timezone.now()
        self.old = RequirementSummary.objects.create(
            user=self.user, title="古い", body_markdown="# 古い", submitted_at=now - timezone.timedelta(days=1),
            mail_status="failed",
        )
        self.new = RequirementSummary.objects.create(
            user=self.other, title="新しい", body_markdown="<script>alert(1)</script>", submitted_at=now,
            handling_status="in_progress",
        )
        RequirementSummary.objects.create(user=self.user, title="下書き", body_markdown="x")

    def test_list_shows_submitted_only_newest_first(self):
        results = self.admin_client.get("/api/admin/summaries/").data["results"]
        self.assertEqual([r["title"] for r in results], ["新しい", "古い"])
        self.assertEqual(results[1]["mail_status"], "failed")
        self.assertEqual(results[0]["user_name"], "別の 人")
        self.assertIn("submitted_at", results[0])

    def test_filter_by_handling_status(self):
        results = self.admin_client.get("/api/admin/summaries/?handling_status=new").data["results"]
        self.assertEqual([r["title"] for r in results], ["古い"])
        self.assertEqual(self.admin_client.get("/api/admin/summaries/?handling_status=x").status_code, 400)

    def test_detail_and_status_change(self):
        detail = self.admin_client.get(f"/api/admin/summaries/{self.new.id}/").data
        self.assertEqual(detail["user_email"], "other@example.com")
        self.assertEqual(detail["body_markdown"], "<script>alert(1)</script>")
        patched = self.admin_client.patch(f"/api/admin/summaries/{self.new.id}/", {"handling_status": "done"})
        self.assertEqual(patched.data["handling_status"], "done")
        self.assertEqual(self.admin_client.get("/api/admin/summaries/?handling_status=done").data["count"], 1)
        bad = self.admin_client.patch(f"/api/admin/summaries/{self.new.id}/", {"handling_status": "zzz"})
        self.assertEqual(bad.status_code, 400)

    def test_general_user_is_forbidden(self):
        self.assertEqual(self.client.get(f"/api/admin/summaries/{self.new.id}/").status_code, 403)
        self.assertEqual(
            self.client.patch(f"/api/admin/summaries/{self.new.id}/", {"handling_status": "done"}).status_code, 403
        )
