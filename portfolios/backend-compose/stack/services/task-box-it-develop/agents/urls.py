from django.urls import path

from . import views

urlpatterns = [
    path("templates/", views.TemplateListView.as_view()),
]
