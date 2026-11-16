import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from agents.usage import usage_summary
from config.exceptions import ApiError

from . import google
from .admins import sync_user_role
from .models import User

logger = logging.getLogger(__name__)


def serialize_user(user):
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
    }


def set_refresh_cookie(response, refresh):
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        str(refresh),
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        path=settings.REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite="Lax",
    )


class GoogleLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        credential = request.data.get("credential")
        if not isinstance(credential, str) or not credential:
            raise ApiError("invalid_request", "credential が必要です")
        try:
            claims = google.verify_google_credential(credential)
        except google.InvalidGoogleToken as exc:
            logger.warning("Googleトークンの検証に失敗: %s", exc)
            raise ApiError(
                "invalid_google_token",
                "Googleでのログインに失敗しました",
                status.HTTP_401_UNAUTHORIZED,
            )

        # フロントから送られた値は信用せず、検証済みのトークンの値だけを使う
        email = claims["email"]
        name = (claims.get("name") or email.split("@")[0])[:150]
        user = User.objects.filter(google_sub=claims["sub"]).first()
        if user is None:
            # GoogleのユーザーIDはOAuthクライアントのプロジェクトごとに異なるため、クライアントを
            # 変えると同じ人でも別のIDになる。確認済みのメールアドレスで既存のユーザーを引き当て、
            # 新しいIDに紐づけ直す（メールアドレスで新規作成すると unique 制約で失敗する）
            user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User(username=email, email=email, google_sub=claims["sub"], display_name=name)
            user.set_unusable_password()
            user.save()
        else:
            updates = []
            if user.google_sub != claims["sub"]:
                user.google_sub = claims["sub"]
                updates.append("google_sub")
            if user.display_name != name:
                user.display_name = name
                updates.append("display_name")
            if updates:
                user.save(update_fields=updates)
        # 管理者かどうかは、ログインのたびに管理者リストのファイルで判定し直す
        sync_user_role(user)

        refresh = RefreshToken.for_user(user)
        response = Response({"access": str(refresh.access_token), "user": serialize_user(user)})
        set_refresh_cookie(response, refresh)
        return response


class DevLoginView(APIView):
    """Googleを使わない開発用ログイン。DEBUG かつ ALLOW_DEV_LOGIN のときだけ存在する。"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        if not settings.ALLOW_DEV_LOGIN:
            raise ApiError("not_found", "見つかりません", status.HTTP_404_NOT_FOUND)
        # 開発用ログインは外部の設定なしで使えることが目的のため、管理者リストのファイルは参照しない
        admin = bool(request.data.get("admin"))
        email = "dev-admin@example.com" if admin else "dev-user@example.com"
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email,
                "google_sub": f"dev-{email}",
                "display_name": "開発用の管理者" if admin else "開発用の依頼者",
            },
        )
        # 既存のユーザーでも、要求された権限に毎回そろえる
        # （sync_admins は管理者リストのファイルを正とするため、開発用のアカウントは権限を落とされる）
        role = User.Role.ADMIN if admin else User.Role.GENERAL
        if (user.role, user.is_staff, user.is_superuser) != (role, admin, admin):
            user.role, user.is_staff, user.is_superuser = role, admin, admin
            user.save(update_fields=["role", "is_staff", "is_superuser"])
        refresh = RefreshToken.for_user(user)
        response = Response({"access": str(refresh.access_token), "user": serialize_user(user)})
        set_refresh_cookie(response, refresh)
        return response


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not raw:
            raise ApiError("not_authenticated", "ログインが必要です", status.HTTP_401_UNAUTHORIZED)
        try:
            refresh = RefreshToken(raw)
            user = User.objects.get(id=refresh["user_id"], is_active=True)
        except (TokenError, KeyError, User.DoesNotExist):
            raise ApiError("not_authenticated", "ログインが必要です", status.HTTP_401_UNAUTHORIZED)
        return Response({"access": str(refresh.access_token), "user": serialize_user(user)})


class LogoutView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(
            settings.REFRESH_COOKIE_NAME, path=settings.REFRESH_COOKIE_PATH, samesite="Lax"
        )
        return response


class MeView(APIView):
    def get(self, request):
        return Response({"user": serialize_user(request.user), "usage": usage_summary(request.user)})
