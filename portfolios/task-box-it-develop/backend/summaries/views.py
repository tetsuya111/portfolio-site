from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from config.exceptions import ApiError

from .models import RequirementSummary
from .services import SUBMITTED_NOTICE, submit_summary


class SubmitSummaryView(APIView):
    def post(self, request, pk):
        # 他人の要件サマリーは存在しないものとして扱う
        summary = get_object_or_404(RequirementSummary, pk=pk, user=request.user)
        submit_summary(summary)
        return Response({"submitted": True, "notice": SUBMITTED_NOTICE})


def serialize_admin_summary(summary, detail=False):
    data = {
        "id": summary.id,
        "title": summary.title,
        "user_name": summary.user.display_name or summary.user.email,
        "submitted_at": summary.submitted_at.isoformat(),
        "handling_status": summary.handling_status,
        "mail_status": summary.mail_status,
    }
    if detail:
        data.update(
            user_email=summary.user.email,
            body_markdown=summary.body_markdown,
            mail_error=summary.mail_error,
        )
    return data


def submitted_summaries():
    return RequirementSummary.objects.filter(submitted_at__isnull=False).select_related("user")


class AdminSummaryListView(ListAPIView):
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        queryset = submitted_summaries().order_by("-submitted_at", "-id")
        handling_status = self.request.query_params.get("handling_status")
        if handling_status:
            if handling_status not in RequirementSummary.HandlingStatus.values:
                raise ApiError("invalid_request", "handling_status の値が不正です")
            queryset = queryset.filter(handling_status=handling_status)
        return queryset

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response([serialize_admin_summary(s) for s in page])


class AdminSummaryDetailView(APIView):
    permission_classes = [IsAdminRole]

    def get_object(self, pk):
        return get_object_or_404(submitted_summaries(), pk=pk)

    def get(self, request, pk):
        return Response(serialize_admin_summary(self.get_object(pk), detail=True))

    def patch(self, request, pk):
        summary = self.get_object(pk)
        handling_status = request.data.get("handling_status")
        if handling_status not in RequirementSummary.HandlingStatus.values:
            raise ApiError("invalid_request", "handling_status の値が不正です")
        summary.handling_status = handling_status
        summary.save(update_fields=["handling_status"])
        return Response(serialize_admin_summary(summary, detail=True))
