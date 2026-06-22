from django.urls import path

from apps.organizer_requests.views import (
    MyOrganizerRequestView,
    OrganizerRequestCancelView,
    OrganizerRequestListCreateView,
    OrganizerRequestProofUploadUrlView,
)

app_name = "organizer_requests"

urlpatterns = [
    path(
        "organizer-requests/proof-upload-url/",
        OrganizerRequestProofUploadUrlView.as_view(),
        name="organizer-request-proof-upload-url",
    ),
    path(
        "organizer-requests/",
        OrganizerRequestListCreateView.as_view(),
        name="organizer-request-list-create",
    ),
    path(
        "organizer-requests/me/",
        MyOrganizerRequestView.as_view(),
        name="organizer-request-me",
    ),
    path(
        "organizer-requests/<uuid:pk>/",
        OrganizerRequestCancelView.as_view(),
        name="organizer-request-cancel",
    ),
]
