from django.urls import path
from apps.users.views import UserProfileView
from apps.users.google_views import GoogleVerifyView
from apps.users.otp_views import OtpSendView, OtpVerifyView

app_name = "users"

urlpatterns = [
    path("profile/", UserProfileView.as_view(), name="user-profile"),
    path("google/verify/", GoogleVerifyView.as_view(), name="google-verify"),
    path("otp/send/", OtpSendView.as_view(), name="otp-send"),
    path("otp/verify/", OtpVerifyView.as_view(), name="otp-verify"),
]
