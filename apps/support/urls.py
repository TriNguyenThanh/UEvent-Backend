from django.urls import path

from apps.support.views import (
    HelpCenterArticleDetailView,
    HelpCenterView,
    LegalDocumentDetailView,
    SupportTicketDetailView,
    SupportTicketListCreateView,
    SupportTicketMessageCreateView,
)

app_name = "support"

urlpatterns = [
    path("help-center/", HelpCenterView.as_view(), name="help-center"),
    path(
        "help-center/articles/<slug:slug>/",
        HelpCenterArticleDetailView.as_view(),
        name="help-center-article-detail",
    ),
    path(
        "legal-documents/<str:document_type>/",
        LegalDocumentDetailView.as_view(),
        name="legal-document-detail",
    ),
    path("tickets/", SupportTicketListCreateView.as_view(), name="ticket-list"),
    path("tickets/<uuid:pk>/", SupportTicketDetailView.as_view(), name="ticket-detail"),
    path(
        "tickets/<uuid:pk>/messages/",
        SupportTicketMessageCreateView.as_view(),
        name="ticket-message-create",
    ),
]
