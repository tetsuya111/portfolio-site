"""対話と、エージェントをまたぐ処理の仲介。

エージェント同士は直接呼び合わない。ここにある関数が Agent.run() を順に呼ぶ。
内部処理のための入力と出力は Message に保存しない（依頼者の対話履歴に表示しないため）。
"""

import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework import status

from agents.agent import Agent
from agents.llm import LLMError, LLMResult
from agents.models import AgentConfig
from config.exceptions import ApiError

from .models import Conversation, Message, PendingAgentCall

logger = logging.getLogger(__name__)

SUMMARY_ITEMS = ["目的", "ほしい機能", "期間のレンジ", "予算のレンジ", "ゴール(最低基準)", "セキュリティ"]
ESTIMATE_AGENT_KEYS = {AgentConfig.MARKET_ESTIMATE, AgentConfig.SELF_ESTIMATE}
TOOL_PREFIX = "call_"
SYSTEM_REQUEST = "【システムからの依頼】"

LLM_FAILED_MESSAGE = "うまく応答できませんでした。少し待ってから、もう一度送ってみてください。"

CHECK_EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "complete": {"type": "boolean"},
        "missing": {"type": "array", "items": {"type": "string", "enum": SUMMARY_ITEMS}},
        "requirements_markdown": {"type": "string"},
    },
    "required": ["complete", "missing", "requirements_markdown"],
    "additionalProperties": False,
}
EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "requirements_markdown": {"type": "string"},
        "completed_items": {"type": "array", "items": {"type": "string", "enum": SUMMARY_ITEMS}},
    },
    "required": ["requirements_markdown", "completed_items"],
    "additionalProperties": False,
}
SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["ok", "error"]},
        "title": {"type": "string"},
        "body_markdown": {"type": "string"},
        "missing_terms": {"type": "array", "items": {"type": "string"}},
        "message": {"type": "string"},
    },
    "required": ["status", "title", "body_markdown", "missing_terms", "message"],
    "additionalProperties": False,
}

ITEMS_TEXT = " / ".join(SUMMARY_ITEMS)
# 確定では、項目の充足判定と要件の抽出を1回の呼び出しでまとめて行う（LLMの呼び出し回数を減らすため）
CHECK_EXTRACT_INPUT = (
    f"{SYSTEM_REQUEST}次の2つを1回で行って。"
    f"(1) 要件サマリーの項目（{ITEMS_TEXT}）がそろっているかの判定。独自の項目は作成せず、定義に従い、"
    "顧客の発言から値がわかる項目だけを「そろっている」とみなし、そろっていない項目を missing に入れて。"
    "判定するのは項目がそろっているかどうかだけで、ほかの観点（表現の良し悪し、追加で聞くべきことなど）は"
    "判定しないで。"
    "(2) 開発したいプロジェクトの要件を網羅的に取得して、requirements_markdown にマークダウン形式で"
    "出力して。顧客が話していないことは書かないで。補完もしないで。"
)
EXTRACT_PREVIEW_INPUT = (
    f"{SYSTEM_REQUEST}開発したいプロジェクトの要件を網羅的に取得して。マークダウン形式で出力して。"
    f"要件サマリーの項目（{ITEMS_TEXT}）のうち、顧客の発言から値がわからない項目は、対話の内容から"
    "妥当な値を補完して。補完した値には必ず末尾に「（仮）」と付け、補完した項目名を completed_items に入れて。"
)
PREVIEW_NOTE = (
    "※「（仮）」と付いた値は、顧客の発言ではなく仮に補完した値です。要件サマリーでも「（仮）」の表記を"
    "そのまま残してください。\n\n"
)


class SummaryIncomplete(ApiError):
    def __init__(self, missing_terms, message=""):
        super().__init__(
            "summary_incomplete",
            "まだ決まっていない項目があるため、まとめを作れませんでした。",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            missing=missing_terms,
            detail=message,
        )


def llm_failed(exc):
    logger.warning("LLM呼び出しに失敗: %s", exc)
    return ApiError("llm_failed", LLM_FAILED_MESSAGE, status.HTTP_502_BAD_GATEWAY)


@dataclass
class SummaryResult:
    title: str
    body_markdown: str
    completed_items: list = field(default_factory=list)


# --- 対話の取得・二重実行の防止 -------------------------------------------------


def get_conversation(user):
    conversation, _ = Conversation.objects.get_or_create(user=user)
    return conversation


def acquire_lock(conversation):
    """実行中フラグを立てる。立てられなければ 409。返り値は release_lock に渡す。"""
    now = timezone.now()
    stale = now - timedelta(seconds=settings.CONVERSATION_LOCK_TIMEOUT_SECONDS)
    updated = (
        Conversation.objects.filter(pk=conversation.pk)
        .filter(Q(processing_started_at__isnull=True) | Q(processing_started_at__lt=stale))
        .update(processing_started_at=now)
    )
    if not updated:
        raise ApiError(
            "conversation_busy",
            "前の処理がまだ終わっていません。少し待ってからもう一度お試しください。",
            status.HTTP_409_CONFLICT,
        )
    return now


def release_lock(conversation, token):
    Conversation.objects.filter(pk=conversation.pk, processing_started_at=token).update(
        processing_started_at=None
    )


@contextmanager
def conversation_lock(conversation):
    token = acquire_lock(conversation)
    try:
        yield
    finally:
        release_lock(conversation, token)


# --- 履歴・シリアライズ -----------------------------------------------------------


def serialize_message(message):
    return {
        "id": message.id,
        "role": message.role,
        "kind": message.kind,
        "agent_key": message.agent_key,
        "content": message.content,
        "metadata": message.metadata,
        "created_at": message.created_at.isoformat(),
    }


def serialize_agent_call(call):
    return {"id": call.id, "agent_key": call.agent_key, "agent_name": call.agent_name}


def build_history(conversation):
    """LLMに渡す履歴。常に user / assistant のテキストの並びにする。"""
    history = []
    for message in conversation.messages.all():
        content = message.content
        if message.kind == Message.Kind.AGENT_RESULT:
            name = message.metadata.get("agent_name") or message.agent_key
            content = f"【「{name}」エージェントが作成した結果】\n{content}"
        history.append({"role": message.role, "content": content})
    return history


def require_user_messages(conversation):
    if not conversation.messages.filter(role=Message.Role.USER).exists():
        raise ApiError(
            "conversation_empty",
            "まずは、作りたいものややりたいことを教えてください。",
            status.HTTP_400_BAD_REQUEST,
        )


def build_call_tools():
    """対話から呼び出せるエージェントを、ヒアリングエージェントのツールとして定義する。

    プロンプトキャッシュの接頭辞を安定させるため、順序は key で固定する。
    """
    return [
        {
            "name": f"{TOOL_PREFIX}{config.key}",
            "description": config.call_description or config.name,
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        }
        for config in AgentConfig.objects.filter(callable_from_chat=True).order_by("key")
    ]


# --- 対話 -------------------------------------------------------------------------


def stream_reply(conversation, user):
    """ヒアリングエージェントの応答を (event, data) の列として返す。"""
    try:
        agent = Agent.load(AgentConfig.HEARING, user)
        result = None
        for item in agent.stream(
            history=build_history(conversation), purpose="chat", tools=build_call_tools()
        ):
            if isinstance(item, LLMResult):
                result = item
            else:
                yield "delta", {"text": item}

        call_keys = [
            name[len(TOOL_PREFIX):] for name in result.tool_calls if name.startswith(TOOL_PREFIX)
        ]
        config = AgentConfig.objects.filter(key__in=call_keys, callable_from_chat=True).first()
        if config is not None:
            # ツールは実行しない。依頼者の許可を待つ（tool use のブロックは保存しない）
            conversation.agent_calls.filter(status=PendingAgentCall.Status.PENDING).update(
                status=PendingAgentCall.Status.DECLINED
            )
            call = PendingAgentCall.objects.create(
                conversation=conversation, agent_key=config.key, agent_name=config.name
            )
            yield "agent_call_request", serialize_agent_call(call)
            return
        if not result.text.strip():
            raise LLMError("空の応答")
        message = Message.objects.create(
            conversation=conversation, role=Message.Role.ASSISTANT, content=result.text
        )
        yield "done", {"message": serialize_message(message)}
    except LLMError as exc:
        logger.warning("LLM呼び出しに失敗: %s", exc)
        yield "error", {"code": "llm_failed", "message": LLM_FAILED_MESSAGE}
    except Exception:
        logger.exception("対話の応答中に予期しないエラー")
        yield "error", {"code": "llm_failed", "message": LLM_FAILED_MESSAGE}


def reply_after_decline(conversation, user, call):
    """確認ダイアログで「いいえ」が選ばれた後の、通常の応答。"""
    history = build_history(conversation)
    note = (
        f"\n\n（画面からの補足: 顧客は「{call.agent_name}」の実行を「いいえ」で断りました。"
        "実行せず、いつもの調子で短く会話を続けてください）"
    )
    if history and history[-1]["role"] == "user":
        history[-1] = {**history[-1], "content": history[-1]["content"] + note}
    else:
        history.append({"role": "user", "content": note.strip()})
    try:
        result = Agent.load(AgentConfig.HEARING, user).run(
            history=history, purpose="chat_after_decline",
            tools=build_call_tools(), tool_choice={"type": "none"},
        )
    except LLMError as exc:
        raise llm_failed(exc)
    if not result.text.strip():
        raise llm_failed("空の応答")
    return Message.objects.create(
        conversation=conversation, role=Message.Role.ASSISTANT, content=result.text
    )


# --- 要件サマリー -----------------------------------------------------------------


def run_summary_agent(user, requirements, preview, report_missing):
    """サマリー作成エージェントで要件サマリーにする。

    report_missing=False（確定の経路）では、不足項目による差し戻しを行わない。
    項目の充足判定は finalize_summary() の1回の呼び出しに集約しているため。
    """
    data = Agent.load(AgentConfig.SUMMARY, user).run(
        (PREVIEW_NOTE + requirements) if preview else requirements,
        purpose="summary", output_schema=SUMMARY_SCHEMA,
    ).parsed()
    if data["status"] == "ok" and data["body_markdown"].strip():
        return data
    if report_missing:
        raise SummaryIncomplete(data.get("missing_terms", []), data.get("message", ""))
    raise llm_failed(f"要件サマリーを作成できませんでした: {data.get('message', '')}")


def finalize_summary(conversation, user):
    """確定。(そろっていない項目, 要件サマリー) を返す。

    充足判定と要件の抽出を1回の呼び出しで行い、そろっていない項目があればそこで打ち切る
    （サマリー作成エージェントは呼ばない）。
    """
    require_user_messages(conversation)
    try:
        checked = Agent.load(AgentConfig.HEARING, user).run(
            CHECK_EXTRACT_INPUT, history=build_history(conversation),
            purpose="check_extract", output_schema=CHECK_EXTRACT_SCHEMA,
        ).parsed()
        missing = [item for item in SUMMARY_ITEMS if item in checked.get("missing", [])]
        if not checked.get("complete") and not missing:
            missing = list(SUMMARY_ITEMS)
        if missing:
            return missing, None
        data = run_summary_agent(user, checked["requirements_markdown"], False, False)
    except LLMError as exc:
        raise llm_failed(exc)
    return [], SummaryResult(title=data["title"], body_markdown=data["body_markdown"])


def build_summary(conversation, user):
    """プレビュー用の要件サマリー。不足している項目は仮の値で補完する。

    見積もりや要約のダウンロードは対話の途中でも試せるよう、充足判定は行わない。
    """
    require_user_messages(conversation)
    try:
        extracted = Agent.load(AgentConfig.HEARING, user).run(
            EXTRACT_PREVIEW_INPUT, history=build_history(conversation),
            purpose="extract_preview", output_schema=EXTRACT_SCHEMA,
        ).parsed()
        data = run_summary_agent(user, extracted["requirements_markdown"], True, True)
    except LLMError as exc:
        raise llm_failed(exc)
    completed = extracted.get("completed_items", [])
    return SummaryResult(
        title=data["title"], body_markdown=data["body_markdown"],
        completed_items=[item for item in SUMMARY_ITEMS if item in completed],
    )


# --- エージェントの実行（確認ダイアログの「はい」、およびボタン） ----------------------


def run_agent(conversation, user, agent_key):
    """エージェントを実行し、結果を対話に agent_result として保存する。

    見積もりなどは対話の途中でも試せるよう、要件サマリーは補完つき（プレビュー）で作成する。
    """
    config = AgentConfig.objects.filter(key=agent_key).first()
    if config is None or config.key == AgentConfig.HEARING:
        raise ApiError("not_found", "エージェントが見つかりません", status.HTTP_404_NOT_FOUND)

    summary = build_summary(conversation, user)
    metadata = {"agent_name": config.name, "completed_items": summary.completed_items}
    if config.key == AgentConfig.SUMMARY:
        content = summary.body_markdown
        metadata.update(is_preview=True, title=summary.title)
    else:
        try:
            result = Agent(config, user).run(summary.body_markdown, purpose="agent_call")
        except LLMError as exc:
            raise llm_failed(exc)
        if not result.text.strip():
            raise llm_failed("空の応答")
        content = result.text
        metadata["is_estimate"] = config.key in ESTIMATE_AGENT_KEYS
    return Message.objects.create(
        conversation=conversation, role=Message.Role.ASSISTANT,
        kind=Message.Kind.AGENT_RESULT, agent_key=config.key,
        content=content, metadata=metadata,
    )


def clear_conversation(conversation):
    conversation.messages.all().delete()
    conversation.agent_calls.all().delete()
