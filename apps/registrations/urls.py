from django.urls import path

from apps.registrations.views import (
    RegistrationListCreateView,
    RegistrationQrAPIView,
)

urlpatterns = [
    path("", RegistrationListCreateView.as_view(), name="registration-list-create"),
    path("<uuid:id>/qr/", RegistrationQrAPIView.as_view(), name="registration-qr"),
]
