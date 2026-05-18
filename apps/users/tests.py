from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIClient

from apps.users.models import Role, UserAuthIdentity, UserRole
from apps.users.services import KeycloakProvisioningService
from common.keycloak_admin import exchange_token_for_user, get_or_create_keycloak_user


class KeycloakProvisioningServiceTests(TestCase):
    def setUp(self):
        self.student_role = Role.objects.create(
            code="student",
            name="Student",
            is_active=True,
        )
        self.User = get_user_model()

    def payload(self, **overrides):
        data = {
            "sub": "0d179e53-ce96-4edf-be4d-4a1d705a4e76",
            "email": "Test@ST.UTC2.EDU.VN",
            "email_verified": True,
            "name": "Test User",
            "picture": "https://example.com/avatar.png",
        }
        data.update(overrides)
        return data

    def test_provisions_new_user_with_email_username_identity_and_student_role(self):
        user = KeycloakProvisioningService.provision_from_payload(self.payload())

        self.assertEqual(user.username, "test@st.utc2.edu.vn")
        self.assertEqual(user.email, "test@st.utc2.edu.vn")
        self.assertEqual(user.full_name, "Test User")
        self.assertEqual(user.avatar_url, "https://example.com/avatar.png")
        self.assertTrue(
            UserAuthIdentity.objects.filter(
                user=user,
                provider=UserAuthIdentity.Provider.KEYCLOAK,
                provider_subject="0d179e53-ce96-4edf-be4d-4a1d705a4e76",
                email_verified=True,
            ).exists()
        )
        self.assertTrue(
            UserRole.objects.filter(
                user=user,
                role=self.student_role,
                is_primary=True,
            ).exists()
        )

    def test_rejects_unverified_email_without_creating_user(self):
        with self.assertRaises(AuthenticationFailed):
            KeycloakProvisioningService.provision_from_payload(
                self.payload(email_verified=False)
            )

        self.assertFalse(self.User.objects.exists())
        self.assertFalse(UserAuthIdentity.objects.exists())

    def test_rejects_missing_email(self):
        with self.assertRaises(AuthenticationFailed):
            KeycloakProvisioningService.provision_from_payload(
                self.payload(email="")
            )

    def test_reuses_existing_identity_and_updates_profile(self):
        user = KeycloakProvisioningService.provision_from_payload(self.payload())

        second = KeycloakProvisioningService.provision_from_payload(
            self.payload(name="Updated Name")
        )
        user.refresh_from_db()

        self.assertEqual(second.pk, user.pk)
        self.assertEqual(user.full_name, "Updated Name")
        self.assertEqual(self.User.objects.count(), 1)
        self.assertEqual(UserAuthIdentity.objects.count(), 1)

    def test_links_existing_email_user_and_assigns_student_role(self):
        existing = self.User.objects.create_user(
            username="legacy-user",
            email="test@st.utc2.edu.vn",
            full_name="Legacy",
        )

        user = KeycloakProvisioningService.provision_from_payload(self.payload())
        existing.refresh_from_db()

        self.assertEqual(user.pk, existing.pk)
        self.assertEqual(existing.username, "test@st.utc2.edu.vn")
        self.assertTrue(UserAuthIdentity.objects.filter(user=existing).exists())
        self.assertTrue(UserRole.objects.filter(user=existing, role=self.student_role).exists())

    def test_rejects_email_conflict_without_merge(self):
        self.User.objects.create_user(
            username="first",
            email="test@st.utc2.edu.vn",
        )
        self.User.objects.create_user(
            username="second",
            email="TEST@st.utc2.edu.vn",
        )

        with self.assertRaises(AuthenticationFailed):
            KeycloakProvisioningService.provision_from_payload(self.payload())

    def test_rejects_banned_user(self):
        self.User.objects.create_user(
            username="test@st.utc2.edu.vn",
            email="test@st.utc2.edu.vn",
            account_status=self.User.AccountStatus.BANNED,
        )

        with self.assertRaises(AuthenticationFailed):
            KeycloakProvisioningService.provision_from_payload(self.payload())

    def test_rejects_missing_student_role(self):
        self.student_role.delete()

        with self.assertRaises(AuthenticationFailed):
            KeycloakProvisioningService.provision_from_payload(self.payload())


class KeycloakAdminClientTests(TestCase):
    @patch("common.keycloak_admin.requests.post")
    @patch("common.keycloak_admin.requests.get")
    def test_get_or_create_keycloak_user_creates_verified_email_user(self, mock_get, mock_post):
        mock_post.side_effect = [
            _Response(200, {"access_token": "service-token"}),
            _Response(201, {}, headers={"Location": "https://keycloak/admin/users/keycloak-id"}),
        ]
        mock_get.return_value = _Response(200, [])

        keycloak_id = get_or_create_keycloak_user("Test@ST.UTC2.EDU.VN")

        self.assertEqual(keycloak_id, "keycloak-id")
        create_payload = mock_post.call_args_list[1].kwargs["json"]
        self.assertEqual(create_payload["email"], "test@st.utc2.edu.vn")
        self.assertEqual(create_payload["username"], "test@st.utc2.edu.vn")
        self.assertTrue(create_payload["emailVerified"])
        self.assertTrue(create_payload["enabled"])

    @patch("common.keycloak_admin.requests.post")
    def test_exchange_token_for_user_requests_refresh_token(self, mock_post):
        mock_post.side_effect = [
            _Response(200, {"access_token": "service-token"}),
            _Response(
                200,
                {
                    "access_token": "access-token",
                    "refresh_token": "refresh-token",
                    "token_type": "Bearer",
                    "expires_in": 300,
                    "refresh_expires_in": 1800,
                },
            ),
        ]

        token_data = exchange_token_for_user("keycloak-user-id")

        exchange_payload = mock_post.call_args_list[1].kwargs["data"]
        self.assertEqual(
            exchange_payload["requested_token_type"],
            "urn:ietf:params:oauth:token-type:refresh_token",
        )
        self.assertEqual(exchange_payload["scope"], "openid email profile")
        self.assertEqual(token_data["refresh_token"], "refresh-token")


@override_settings(GOOGLE_OAUTH_CLIENT_IDS=["google-web-client-id"])
class GoogleVerifyViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username="test@st.utc2.edu.vn",
            email="test@st.utc2.edu.vn",
        )

    @patch("apps.users.google_views.KeycloakJWTAuthentication.authenticate_token")
    @patch("apps.users.google_views.exchange_token_for_user")
    @patch("apps.users.google_views.get_or_create_keycloak_user")
    @patch("apps.users.google_views.google_id_token.verify_oauth2_token")
    def test_google_verify_returns_keycloak_tokens_and_links_identity(
        self,
        mock_verify_google,
        mock_get_or_create_user,
        mock_exchange_token,
        mock_authenticate_token,
    ):
        mock_verify_google.return_value = {
            "sub": "google-subject",
            "email": "Test@ST.UTC2.EDU.VN",
            "email_verified": True,
            "name": "Test User",
            "given_name": "Test",
            "family_name": "User",
            "picture": "https://example.com/avatar.png",
        }
        mock_get_or_create_user.return_value = "keycloak-user-id"
        mock_exchange_token.return_value = {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "token_type": "Bearer",
            "expires_in": 300,
            "refresh_expires_in": 1800,
        }
        mock_authenticate_token.return_value = (self.user, {"sub": "keycloak-user-id"})

        response = self.client.post(
            reverse("users:google-verify"),
            {"id_token": "google-id-token"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["access_token"], "access-token")
        mock_verify_google.assert_called_once()
        mock_get_or_create_user.assert_called_once_with(
            "test@st.utc2.edu.vn",
            full_name="Test User",
            first_name="Test",
            last_name="User",
            avatar_url="https://example.com/avatar.png",
        )
        self.assertTrue(
            UserAuthIdentity.objects.filter(
                user=self.user,
                provider=UserAuthIdentity.Provider.GOOGLE,
                provider_subject="google-subject",
                email_verified=True,
            ).exists()
        )

    @patch("apps.users.google_views.google_id_token.verify_oauth2_token")
    def test_google_verify_rejects_unverified_email(self, mock_verify_google):
        mock_verify_google.return_value = {
            "sub": "google-subject",
            "email": "test@st.utc2.edu.vn",
            "email_verified": False,
        }

        response = self.client.post(
            reverse("users:google-verify"),
            {"id_token": "google-id-token"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "invalid_credentials")

    @patch("apps.users.google_views.google_id_token.verify_oauth2_token")
    def test_google_verify_rejects_invalid_token(self, mock_verify_google):
        mock_verify_google.side_effect = ValueError("invalid audience")

        response = self.client.post(
            reverse("users:google-verify"),
            {"id_token": "bad-token"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "invalid_credentials")


class RepairKeycloakUsersCommandTests(TestCase):
    def setUp(self):
        self.student_role = Role.objects.create(
            code="student",
            name="Student",
            is_active=True,
        )
        self.User = get_user_model()

    def test_dry_run_does_not_change_user(self):
        user = self._legacy_keycloak_user()
        out = StringIO()

        call_command("repair_keycloak_users", "--dry-run", stdout=out)
        user.refresh_from_db()

        self.assertEqual(user.username, "0d179e53-ce96-4edf-be4d-4a1d705a4e76")
        self.assertFalse(UserRole.objects.filter(user=user).exists())
        self.assertIn("DRY-RUN", out.getvalue())

    def test_apply_updates_uuid_username_and_assigns_student_role(self):
        user = self._legacy_keycloak_user()
        out = StringIO()

        call_command("repair_keycloak_users", "--apply", stdout=out)
        user.refresh_from_db()

        self.assertEqual(user.username, "test@st.utc2.edu.vn")
        self.assertTrue(UserRole.objects.filter(user=user, role=self.student_role).exists())
        self.assertIn("APPLIED", out.getvalue())

    def _legacy_keycloak_user(self):
        user = self.User.objects.create_user(
            username="0d179e53-ce96-4edf-be4d-4a1d705a4e76",
            email="Test@ST.UTC2.EDU.VN",
        )
        UserAuthIdentity.objects.create(
            user=user,
            provider=UserAuthIdentity.Provider.KEYCLOAK,
            provider_subject="0d179e53-ce96-4edf-be4d-4a1d705a4e76",
            email_verified=True,
        )
        return user


class _Response:
    def __init__(self, status_code, payload, headers=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._payload
