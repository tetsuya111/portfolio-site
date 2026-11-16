from django.urls import path

from . import views

urlpatterns = [
    path("conversation/", views.ConversationView.as_view()),
    path("conversation/messages/", views.MessageCreateView.as_view()),
    path("conversation/agent-calls/<int:pk>/approve/", views.AgentCallView.as_view(approve=True)),
    path("conversation/agent-calls/<int:pk>/decline/", views.AgentCallView.as_view(approve=False)),
    path("conversation/clear/", views.ClearView.as_view()),
    path("conversation/actions/finalize/", views.FinalizeView.as_view()),
    path("conversation/actions/summary-download/", views.SummaryDownloadView.as_view()),
    path("conversation/actions/market-estimate/", views.MarketEstimateView.as_view()),
    path("conversation/actions/self-estimate/", views.SelfEstimateView.as_view()),
]
