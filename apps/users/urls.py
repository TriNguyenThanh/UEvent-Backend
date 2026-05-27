from django.urls import path
from apps.users.auth_views import MobileLogoutView, MobileTokenRefreshView
from apps.users.views import (
    UserProfileEmailChangeView,
    UserProfileEmailOtpView,
    UserProfileNewEmailOtpView,
    UserProfileView,
)
from apps.users.google_views import GoogleVerifyView
from apps.users.otp_views import OtpSendView, OtpVerifyView

app_name = "users"

urlpatterns = [
    path("profile/", UserProfileView.as_view(), name="user-profile"),
    path(
        "profile/email/otp/",
        UserProfileEmailOtpView.as_view(),
        name="user-profile-email-otp",
    ),
    path(
        "profile/email/new/otp/",
        UserProfileNewEmailOtpView.as_view(),
        name="user-profile-new-email-otp",
    ),
    path(
        "profile/email/",
        UserProfileEmailChangeView.as_view(),
        name="user-profile-email-change",
    ),
    path("refresh/", MobileTokenRefreshView.as_view(), name="mobile-token-refresh"),
    path("logout/", MobileLogoutView.as_view(), name="mobile-logout"),
    path("google/verify/", GoogleVerifyView.as_view(), name="google-verify"),
    path("otp/send/", OtpSendView.as_view(), name="otp-send"),
    path("otp/verify/", OtpVerifyView.as_view(), name="otp-verify"),
]
