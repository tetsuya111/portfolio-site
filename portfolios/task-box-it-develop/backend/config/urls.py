from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # フロントエンドの管理者画面（/admin/...）と紛れないよう、Djangoの管理サイトは別パスにする
    path("django-admin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/", include("agents.urls")),
    path("api/", include("chat.urls")),
    path("api/", include("summaries.urls")),
]
