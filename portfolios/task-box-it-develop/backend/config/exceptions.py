"""APIのエラー応答を {code, message, ...} の形に統一する。"""

from rest_framework import status
from rest_framework.exceptions import APIException, NotAuthenticated, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import exception_handler


class ApiError(APIException):
    """code つきのエラー。extra は応答の本文にそのまま展開される。"""

    def __init__(self, code, message, status_code=status.HTTP_400_BAD_REQUEST, **extra):
        super().__init__(detail=message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.extra = extra


def api_exception_handler(exc, context):
    if isinstance(exc, ApiError):
        return Response(
            {"code": exc.code, "message": exc.message, **exc.extra},
            status=exc.status_code,
        )
    response = exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, NotAuthenticated) or response.status_code == 401:
        code = "not_authenticated"
    elif isinstance(exc, PermissionDenied):
        code = "forbidden"
    elif response.status_code == 404:
        code = "not_found"
    else:
        code = "invalid_request"
    response.data = {"code": code, "message": "リクエストを処理できませんでした", "detail": response.data}
    return response
