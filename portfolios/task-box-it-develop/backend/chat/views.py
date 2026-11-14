import json

from django.conf import settings
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.models import AgentConfig
from agents.usage import ensure_within_limit
from config.exceptions import ApiError
from summaries.services import create_draft

from . import services
from .models import Message, PendingAgentCall


def sse(event, data):
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class ConversationView(APIView):
    def get(self, request):
        conversation = services.get_conversation(request.user)
        pending = conversation.agent_calls.filter(status=PendingAgentCall.Status.PENDING).last()
        return Response(
            {
                "messages": [services.serialize_message(m) for m in conversation.messages.all()],
                "pending_agent_call": services.serialize_agent_call(pending) if pending else None,
            }
        )


class MessageCreateView(APIView):
    def post(self, request):
        content = request.data.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ApiError("invalid_request", "メッセージを入力してください")
        if len(content) > settings.MESSAGE_MAX_LENGTH:
            raise ApiError(
                "message_too_long",
                f"メッセージが長すぎます（{settings.MESSAGE_MAX_LENGTH}文字まで）",
            )
        ensure_within_limit(request.user)
        conversation = services.get_conversation(request.user)
        token = services.acquire_lock(conversation)

        def events():
            # 実行中フラグは、クライアントの切断も含めてストリームの終了時に必ず解除する
            try:
                Message.objects.create(
                    conversation=conversation, role=Message.Role.USER, content=content.strip()
                )
                for event, data in services.stream_reply(conversation, request.user):
                    yield sse(event, data)
            finally:
                services.release_lock(conversation, token)

        response = StreamingHttpResponse(events(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class AgentCallView(APIView):
    """確認ダイアログの「はい / いいえ」。"""

    approve = True

    def post(self, request, pk):
        conversation = services.get_conversation(request.user)
        call = get_object_or_404(PendingAgentCall, pk=pk, conversation=conversation)
        if call.status != PendingAgentCall.Status.PENDING:
            raise ApiError("already_answered", "この確認には回答済みです", status.HTTP_409_CONFLICT)
        ensure_within_limit(request.user)
        with services.conversation_lock(conversation):
            # 実行に失敗しても許可待ちのまま残さない（依頼者は対話を続けられる）
            call.status = (
                PendingAgentCall.Status.APPROVED if self.approve
                else PendingAgentCall.Status.DECLINED
            )
            call.save(update_fields=["status"])
            if self.approve:
                message = services.run_agent(conversation, request.user, call.agent_key)
            else:
                message = services.reply_after_decline(conversation, request.user, call)
        return Response({"message": services.serialize_message(message)})


class ClearView(APIView):
    def post(self, request):
        conversation = services.get_conversation(request.user)
        with services.conversation_lock(conversation):
            services.clear_conversation(conversation)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LLMActionView(APIView):
    """ボタン操作。ボタンを押すこと自体を許可とみなし、確認ダイアログは挟まない。"""

    def post(self, request):
        ensure_within_limit(request.user)
        conversation = services.get_conversation(request.user)
        with services.conversation_lock(conversation):
            return Response(self.perform(conversation, request.user))


class FinalizeView(LLMActionView):
    def perform(self, conversation, user):
        missing, summary = services.finalize_summary(conversation, user)
        if missing:
            return {"complete": False, "missing": missing}
        draft = create_draft(user, summary.title, summary.body_markdown)
        return {
            "complete": True,
            "summary": {"id": draft.id, "title": draft.title, "body_markdown": draft.body_markdown},
        }


class SummaryDownloadView(LLMActionView):
    def perform(self, conversation, user):
        summary = services.build_summary(conversation, user)
        return {
            "title": summary.title,
            "body_markdown": summary.body_markdown,
            "completed_items": summary.completed_items,
        }


class EstimateView(LLMActionView):
    agent_key = None

    def perform(self, conversation, user):
        message = services.run_agent(conversation, user, self.agent_key)
        return {"message": services.serialize_message(message)}


class MarketEstimateView(EstimateView):
    agent_key = AgentConfig.MARKET_ESTIMATE


class SelfEstimateView(EstimateView):
    agent_key = AgentConfig.SELF_ESTIMATE
