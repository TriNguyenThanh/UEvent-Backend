from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.system_admin.services.auth_service import AdminAuthService


class AdminKeycloakAuthServiceTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_user(
            username="admin",
            email="admin@example.com",
            password="unused",
            is_staff=True,
            is_superuser=True,
        )

    @override_settings(
        KEYCLOAK_CLIENT_ID="uevent-admin",
        KEYCLOAK_CLIENT_SECRET="secret",
        KEYCLOAK_SCOPE="openid email profile",
        KEYCLOAK_TOKEN_URL="https://auth.example.test/token",
        KEYCLOAK_TOKEN_TIMEOUT=5,
    )
    @patch("apps.system_admin.services.auth_service.AdminAuditService.log_action")
    @patch("apps.system_admin.services.auth_service.KeycloakJWTAuthentication.authenticate_token")
    @patch("apps.system_admin.services.auth_service.requests.post")
    def test_admin_login_exchanges_password_with_keycloak(self, mock_post, mock_authenticate_token, mock_log_action):
        response = Mock(status_code=200)
        response.json.return_value = {
            "access_token": "keycloak-access",
            "refresh_token": "keycloak-refresh",
        }
        mock_post.return_value = response
        mock_authenticate_token.return_value = (self.admin_user, {"sub": "keycloak-sub"})

        result = AdminAuthService.admin_login(username="admin", password="secret")

        self.assertEqual(result["access"], "keycloak-access")
        self.assertEqual(result["refresh"], "keycloak-refresh")
        self.assertEqual(result["user"]["email"], "admin@example.com")
        mock_post.assert_called_once()
        posted_data = mock_post.call_args.kwargs["data"]
        self.assertEqual(posted_data["grant_type"], "password")
        self.assertEqual(posted_data["client_id"], "uevent-admin")
        self.assertEqual(posted_data["client_secret"], "secret")
        self.assertEqual(posted_data["username"], "admin")
        self.assertEqual(posted_data["password"], "secret")
        mock_authenticate_token.assert_called_once_with("keycloak-access")
        mock_log_action.assert_called_once()

    @override_settings(
        KEYCLOAK_CLIENT_ID="uevent-admin",
        KEYCLOAK_CLIENT_SECRET="",
        KEYCLOAK_TOKEN_URL="https://auth.example.test/token",
        KEYCLOAK_TOKEN_TIMEOUT=5,
    )
    @patch("apps.system_admin.services.auth_service.KeycloakJWTAuthentication.authenticate_token")
    @patch("apps.system_admin.services.auth_service.requests.post")
    def test_refresh_token_exchanges_refresh_with_keycloak(self, mock_post, mock_authenticate_token):
        response = Mock(status_code=200)
        response.json.return_value = {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
        }
        mock_post.return_value = response
        mock_authenticate_token.return_value = (self.admin_user, {"sub": "keycloak-sub"})

        result = AdminAuthService.refresh_token(refresh="old-refresh")

        self.assertEqual(result, {"access": "new-access", "refresh": "new-refresh"})
        posted_data = mock_post.call_args.kwargs["data"]
        self.assertEqual(posted_data["grant_type"], "refresh_token")
        self.assertEqual(posted_data["refresh_token"], "old-refresh")


class AdminKeycloakAuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = get_user_model().objects.create_user(
            username="admin",
            email="admin@example.com",
            password="unused",
            is_staff=True,
            is_superuser=True,
        )
        self.login_result = {
            "access": "keycloak-access",
            "refresh": "keycloak-refresh",
            "user": {
                "id": str(self.admin_user.pk),
                "username": self.admin_user.username,
                "full_name": self.admin_user.full_name,
                "email": self.admin_user.email,
                "avatar_url": self.admin_user.avatar_url,
                "is_superuser": self.admin_user.is_superuser,
            },
        }

    @patch("apps.system_admin.views.auth_views.AdminAuthService.admin_login")
    def test_login_endpoint_returns_frontend_token_contract(self, mock_admin_login):
        mock_admin_login.return_value = self.login_result

        response = self.client.post(
            reverse("system_admin:admin-login"),
            {"username": "admin", "password": "secret"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["access"], "keycloak-access")
        self.assertEqual(response.data["data"]["refresh"], "keycloak-refresh")
        self.assertEqual(response.data["data"]["user"]["email"], "admin@example.com")
        mock_admin_login.assert_called_once_with(username="admin", password="secret")

    @patch("apps.system_admin.views.auth_views.AdminAuthService.refresh_token")
    def test_refresh_endpoint_returns_new_access_token(self, mock_refresh_token):
        mock_refresh_token.return_value = {"access": "new-access", "refresh": "new-refresh"}

        response = self.client.post(
            reverse("system_admin:admin-token-refresh"),
            {"refresh": "old-refresh"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"], {"access": "new-access", "refresh": "new-refresh"})
        mock_refresh_token.assert_called_once_with(refresh="old-refresh")

    @patch("apps.system_admin.views.auth_views.AdminAuthService.admin_logout")
    def test_logout_endpoint_accepts_refresh_token(self, mock_admin_logout):
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.post(
            reverse("system_admin:admin-logout"),
            {"refresh": "keycloak-refresh"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        mock_admin_logout.assert_called_once_with(actor=self.admin_user, refresh="keycloak-refresh")
