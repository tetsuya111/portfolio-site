"""テスト共通の土台。LLMは必ず偽のクライアントに差し替える。"""

from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from agents.testing import FakeLLMClient


@override_settings(
    LLM_CLIENT_CLASS="agents.testing.FakeLLMClient",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    ADMIN_EMAIL="owner@example.com",
    DAILY_TOKEN_LIMIT=300000,
    # ローカルの .env やローカルのファイルに左右されないよう固定する
    ALLOW_DEV_LOGIN=False,
    ADMIN_EMAILS_FILE="admin_emails.for-tests-does-not-exist.txt",
    GOOGLE_OAUTH_CLIENT_ID="test-client-id",
)
class ApiTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_agents", verbosity=0, stdout=open_null())
        cls.user = make_user("irai@example.com", "依頼 太郎")
        cls.other = make_user("other@example.com", "別の 人")
        cls.admin = make_user("owner@example.com", "管理者", role=User.Role.ADMIN)

    def setUp(self):
        FakeLLMClient.reset()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def as_user(self, user):
        client = APIClient()
        if user is not None:
            client.force_authenticate(user)
        return client


def make_user(email, name, role=User.Role.GENERAL):
    return User.objects.create(
        username=email, email=email, google_sub=f"sub-{email}", display_name=name, role=role
    )


def open_null():
    import io

    return io.StringIO()


def read_sse(response):
    """StreamingHttpResponse を (event, data) のリストにする。"""
    import json

    body = b"".join(response.streaming_content).decode()
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        events.append((lines["event"], json.loads(lines["data"])))
    return events
