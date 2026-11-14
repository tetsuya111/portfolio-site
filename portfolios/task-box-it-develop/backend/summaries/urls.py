from django.urls import path

from . import views

urlpatterns = [
    path("summaries/<int:pk>/submit/", views.SubmitSummaryView.as_view()),
    path("admin/summaries/", views.AdminSummaryListView.as_view()),
    path("admin/summaries/<int:pk>/", views.AdminSummaryDetailView.as_view()),
]
