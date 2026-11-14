import logging
import re
import unicodedata

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from .models import RequirementSummary

logger = logging.getLogger(__name__)

SUBMITTED_NOTICE = "管理者からのメールをお待ちください"
DEFAULT_TITLE = "無題の要件サマリー"


def clean_title(title):
    """依頼者由来の文字列をメールの件名に使うため、制御文字を除去して1行・100文字にする。"""
    cleaned = "".join(" " if unicodedata.category(ch).startswith("C") else ch for ch in title or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:100] or DEFAULT_TITLE


def create_draft(user, title, body_markdown):
    # 下書きは依頼者1人につき最新の1件だけ残す
    RequirementSummary.objects.filter(user=user, submitted_at__isnull=True).delete()
    return RequirementSummary.objects.create(
        user=user, title=clean_title(title), body_markdown=body_markdown
    )


def send_summary_mail(summary):
    if not settings.ADMIN_EMAIL:
        raise RuntimeError("ADMIN_EMAIL が設定されていません")
    message = EmailMessage(
        subject=f"【タスク百葉箱】要件サマリー「{summary.title}」",
        body=f"{clean_title(summary.user.display_name or summary.user.email)}さんから要件サマリーが届きました",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.ADMIN_EMAIL],
    )
    message.attach("requirement_summary.md", summary.body_markdown, "text/markdown")
    message.send(fail_silently=False)


def submit_summary(summary):
    """下書きを送信済みにしてメールを送る。何度呼ばれても保存・送信は1回だけ。"""
    updated = RequirementSummary.objects.filter(
        pk=summary.pk, submitted_at__isnull=True
    ).update(submitted_at=timezone.now())
    if not updated:
        return False
    summary.refresh_from_db()
    try:
        send_summary_mail(summary)
    except Exception as exc:  # メールの失敗で、保存済みの要件サマリーと依頼者への応答を失敗にしない
        logger.error("要件サマリー %s のメール送信に失敗: %s", summary.pk, exc)
        summary.mail_status = RequirementSummary.MailStatus.FAILED
        summary.mail_error = str(exc)[:2000]
    else:
        summary.mail_status = RequirementSummary.MailStatus.SENT
    summary.save(update_fields=["mail_status", "mail_error"])
    return True
