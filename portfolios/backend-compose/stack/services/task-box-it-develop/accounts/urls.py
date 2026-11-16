from django.urls import path

from . import views

urlpatterns = [
    path("auth/google/", views.GoogleLoginView.as_view()),
    path("auth/dev-login/", views.DevLoginView.as_view()),
    path("auth/refresh/", views.RefreshView.as_view()),
    path("auth/logout/", views.LogoutView.as_view()),
    path("me/", views.MeView.as_view()),
]
