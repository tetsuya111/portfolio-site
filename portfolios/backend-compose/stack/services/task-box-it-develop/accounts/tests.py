import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.core.management import call_command

from accounts import admins, google
from accounts.models import User
from config.testing import ApiTestCase

CLAIMS = {"sub": "g-123", "email": "new@example.com", "email_verified": True, "name": "新規 花子"}


class GoogleLoginTests(ApiTestCase):
    def login(self, claims=CLAIMS, side_effect=None):
        with mock.patch.object(
            google, "verify_google_credential", return_value=claims, side_effect=side_effect
        ):
            return self.as_user(None).post("/api/auth/google/", {"credential": "token"})

    def test_creates_general_user_on_first_login(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(google_sub="g-123")
        self.assertEqual(user.role, User.Role.GENERAL)
        self.assertEqual(user.display_name, "新規 花子")
        self.assertFalse(user.has_usable_password())
        self.assertIn("access", response.data)
        cookie = response.cookies["refresh_token"]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(cookie["path"], "/api/auth/")

    def test_existing_user_is_reused(self):
        self.login()
        self.login()
        self.assertEqual(User.objects.filter(google_sub="g-123").count(), 1)

    def test_existing_email_is_relinked_when_the_google_id_changes(self):
        # OAuthクライアント（GCPプロジェクト）を変えると、同じ人でもGoogleのユーザーIDが変わる
        before = User.objects.count()
        claims = {**CLAIMS, "sub": "g-new-project", "email": self.user.email}
        response = self.login(claims=claims)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["id"], self.user.id)
        self.user.refresh_from_db()
        self.assertEqual(self.user.google_sub, "g-new-project")
        # 同じメールアドレスのユーザーが二重に作られない
        self.assertEqual(User.objects.count(), before)

    def test_invalid_token_is_rejected(self):
        response = self.login(side_effect=google.InvalidGoogleToken("bad"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], "invalid_google_token")

    def test_refresh_and_logout(self):
        client = self.as_user(None)
        with mock.patch.object(google, "verify_google_credential", return_value=CLAIMS):
            client.post("/api/auth/google/", {"credential": "token"})
        refreshed = client.post("/api/auth/refresh/")
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(refreshed.data["user"]["email"], "new@example.com")
        client.post("/api/auth/logout/")
        client.cookies.pop("refresh_token", None)
        self.assertEqual(client.post("/api/auth/refresh/").status_code, 401)


class DevLoginTests(ApiTestCase):
    def test_dev_login_is_disabled_by_default(self):
        self.assertEqual(self.as_user(None).post("/api/auth/dev-login/").status_code, 404)

    def test_dev_login_when_enabled(self):
        with self.settings(ALLOW_DEV_LOGIN=True):
            response = self.as_user(None).post("/api/auth/dev-login/", {"admin": True}, format="json")
        self.assertEqual(response.data["user"]["role"], "admin")

    def test_dev_login_restores_admin_after_sync_admins(self):
        # 管理者リストのファイルに載っていない開発用アカウントは sync_admins で権限を落とされるが、
        # 開発用ログインはファイルを参照せず、毎回要求された権限にそろえる
        with self.settings(ALLOW_DEV_LOGIN=True):
            client = self.as_user(None)
            client.post("/api/auth/dev-login/", {"admin": True}, format="json")
            User.objects.filter(email="dev-admin@example.com").update(
                role=User.Role.GENERAL, is_staff=False, is_superuser=False
            )
            response = client.post("/api/auth/dev-login/", {"admin": True}, format="json")
        self.assertEqual(response.data["user"]["role"], "admin")
        user = User.objects.get(email="dev-admin@example.com")
        self.assertTrue(user.is_staff and user.is_superuser)


class PermissionTests(ApiTestCase):
    def test_unauthenticated_is_rejected(self):
        for path in ("/api/me/", "/api/conversation/", "/api/templates/", "/api/admin/summaries/"):
            response = self.as_user(None).get(path)
            self.assertEqual(response.status_code, 401, path)
            self.assertEqual(response.data["code"], "not_authenticated")

    def test_general_user_cannot_use_admin_api(self):
        response = self.client.get("/api/admin/summaries/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.as_user(self.admin).get("/api/admin/summaries/").status_code, 200)

    def test_me_returns_role_and_usage(self):
        data = self.client.get("/api/me/").data
        self.assertEqual(data["user"]["role"], "general")
        self.assertEqual(
            data["usage"],
            {
                "used": 0, "limit": 300000, "limit_reached": False,
                "remaining_percent": 100, "unlimited": False,
            },
        )


class AdminEmailsFileTests(ApiTestCase):
    """管理者は、テキストファイルに書かれたメールアドレスで決まる。"""

    def setUp(self):
        super().setUp()
        admins.reset_cache()
        self.addCleanup(admins.reset_cache)

    def write_file(self, *lines):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "admin_emails.txt"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        admins.reset_cache()
        return path

    def use_file(self, *lines):
        return self.settings(ADMIN_EMAILS_FILE=str(self.write_file(*lines)))

    def login(self, email, sub):
        claims = {"sub": sub, "email": email, "email_verified": True, "name": "だれか"}
        with mock.patch.object(google, "verify_google_credential", return_value=claims):
            return self.as_user(None).post("/api/auth/google/", {"credential": "token"})

    def test_listed_email_becomes_admin_on_login(self):
        # コメント・空行・大文字小文字・前後の空白は無視する
        with self.use_file("# 管理者", "", "   BOSS@Example.com   "):
            response = self.login("boss@example.com", "g-boss")
        self.assertEqual(response.data["user"]["role"], "admin")
        user = User.objects.get(google_sub="g-boss")
        self.assertTrue(user.is_staff and user.is_superuser)

    def test_unlisted_email_stays_general(self):
        with self.use_file("boss@example.com"):
            response = self.login("guest@example.com", "g-guest")
        self.assertEqual(response.data["user"]["role"], "general")

    def test_removed_email_loses_admin_on_next_login(self):
        with self.use_file("# 誰もいない"):
            response = self.login(self.admin.email, self.admin.google_sub)
        self.assertEqual(response.data["user"]["role"], "general")
        self.admin.refresh_from_db()
        self.assertFalse(self.admin.is_staff or self.admin.is_superuser)

    def test_missing_file_does_not_break_login(self):
        # ApiTestCase の既定は存在しないパス
        with self.assertLogs("accounts.admins", "WARNING"):
            response = self.login("guest@example.com", "g-guest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["role"], "general")
        self.assertEqual(admins.load_admin_emails(), frozenset())

    def test_relative_path_is_resolved_from_base_dir(self):
        with self.settings(ADMIN_EMAILS_FILE="admin_emails.txt"):
            self.assertEqual(admins.admin_emails_path(), Path(settings.BASE_DIR) / "admin_emails.txt")

    def test_file_is_reread_after_change(self):
        path = self.write_file("owner@example.com")
        with self.settings(ADMIN_EMAILS_FILE=str(path)):
            self.assertTrue(admins.is_admin_email("owner@example.com"))
            path.write_text("someone-else@example.com\n", encoding="utf-8")
            admins.reset_cache()
            self.assertFalse(admins.is_admin_email("owner@example.com"))

    def test_sync_admins_command(self):
        output = StringIO()
        with self.use_file("irai@example.com"):
            call_command("sync_admins", stdout=output)
        self.user.refresh_from_db()
        self.admin.refresh_from_db()
        self.assertEqual(self.user.role, User.Role.ADMIN)
        self.assertTrue(self.user.is_staff)
        # ファイルに載っていない既存の管理者は一般ユーザーに戻る
        self.assertEqual(self.admin.role, User.Role.GENERAL)
        self.assertIn("管理者 1件", output.getvalue())
