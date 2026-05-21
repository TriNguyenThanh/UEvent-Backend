from io import StringIO
import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIClient

from apps.users.models import Role, UserAuthIdentity, UserRole
from apps.users.services import KeycloakProvisioningService
from common import otp as otp_service
from common.authentication import KeycloakJWTAuthentication
from common.keycloak_admin import (
    KeycloakAdminError,
    exchange_token_for_user,
    get_or_create_keycloak_user,
    logout_keycloak_refresh_token,
    refresh_keycloak_token,
)


class KeycloakProvisioningServiceTests(TestCase):
    def setUp(self):
        self.student_role = Role.objects.create(
            code="student",
            name="Student",
            is_active=True,
        )
        self.organizer_role = Role.objects.create(
            code="organizer",
            name="Organizer",
            is_active=True,
        )
        self.system_admin_role = Role.objects.create(
            code="system_admin",
            name="System Admin",
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

    def test_syncs_user_roles_from_keycloak_realm_roles(self):
        user = KeycloakProvisioningService.provision_from_payload(
            self.payload(
                realm_access={
                    "roles": [
                        "student",
                        "organizer",
                        "super_admin",
                        "offline_access",
                        "uma_authorization",
                        "default-roles-uevent",
                    ]
                }
            )
        )
        user.refresh_from_db()

        role_codes = set(
            UserRole.objects.filter(user=user).values_list("role__code", flat=True)
        )
        self.assertEqual(role_codes, {"student", "organizer", "system_admin"})
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_rejects_unverified_email_without_creating_user(self):
        with self.assertRaises(AuthenticationFailed):
            KeycloakProvisioningService.provision_from_payload(
                self.payload(email_verified=False)
            )

        self.assertFalse(self.User.objects.exists())
        self.assertFalse(UserAuthIdentity.objects.exists())

    def test_rejects_missing_email(self):
        with self.assertRaises(AuthenticationFailed):
            KeycloakProvisioningService.provision_from_payload(self.payload(email=""))

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
        self.assertTrue(
            UserRole.objects.filter(user=existing, role=self.student_role).exists()
        )

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


class KeycloakJWTAuthenticationCacheTests(TestCase):
    def setUp(self):
        cache.clear()
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username="test@st.utc2.edu.vn",
            email="test@st.utc2.edu.vn",
        )
        self.auth = KeycloakJWTAuthentication()
        self.token = "access-token"

    def tearDown(self):
        cache.clear()

    def payload(self):
        return {
            "sub": "keycloak-user-id",
            "email": "test@st.utc2.edu.vn",
            "email_verified": True,
            "exp": int(time.time()) + 300,
        }

    @override_settings(KEYCLOAK_AUTH_USER_CACHE_TTL=300)
    @patch("common.authentication.KeycloakProvisioningService.provision_from_payload")
    @patch.object(KeycloakJWTAuthentication, "_decode_token")
    def test_reuses_cached_user_without_reprovisioning_same_token(
        self,
        mock_decode_token,
        mock_provision,
    ):
        mock_decode_token.return_value = self.payload()
        mock_provision.return_value = self.user

        first_user, _ = self.auth.authenticate_token(self.token)
        second_user, _ = self.auth.authenticate_token(self.token)

        self.assertEqual(first_user.pk, self.user.pk)
        self.assertEqual(second_user.pk, self.user.pk)
        self.assertEqual(mock_decode_token.call_count, 2)
        mock_provision.assert_called_once()

    @override_settings(KEYCLOAK_AUTH_USER_CACHE_TTL=300)
    @patch("common.authentication.KeycloakProvisioningService.provision_from_payload")
    @patch.object(KeycloakJWTAuthentication, "_decode_token")
    def test_cached_user_status_is_checked_each_request(
        self,
        mock_decode_token,
        mock_provision,
    ):
        mock_decode_token.return_value = self.payload()
        mock_provision.return_value = self.user

        self.auth.authenticate_token(self.token)
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate_token(self.token)
        mock_provision.assert_called_once()


class KeycloakAdminClientTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch("common.keycloak_admin.requests.post")
    @patch("common.keycloak_admin.requests.get")
    def test_get_or_create_keycloak_user_creates_verified_email_user(
        self, mock_get, mock_post
    ):
        mock_post.side_effect = [
            _Response(200, {"access_token": "service-token"}),
            _Response(
                201,
                {},
                headers={"Location": "https://keycloak/admin/users/keycloak-id"},
            ),
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
        self.assertEqual(
            exchange_payload["scope"], "openid email profile offline_access"
        )
        self.assertEqual(token_data["refresh_token"], "refresh-token")

    @override_settings(
        KEYCLOAK_LOGOUT_URL="https://auth.example.test/logout",
        KEYCLOAK_ADMIN_CLIENT_ID="backend-client",
        KEYCLOAK_ADMIN_CLIENT_SECRET="backend-secret",
        KEYCLOAK_TOKEN_TIMEOUT=7,
    )
    @patch("common.keycloak_admin.requests.post")
    def test_logout_keycloak_refresh_token_uses_backend_client(self, mock_post):
        mock_post.return_value = _Response(204, {})

        logout_keycloak_refresh_token("refresh-token")

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["data"]["client_id"], "backend-client")
        self.assertEqual(kwargs["data"]["client_secret"], "backend-secret")
        self.assertEqual(kwargs["data"]["refresh_token"], "refresh-token")
        self.assertEqual(kwargs["timeout"], 7)

    @override_settings(
        KEYCLOAK_TOKEN_URL="https://auth.example.test/token",
        KEYCLOAK_ADMIN_CLIENT_ID="backend-client",
        KEYCLOAK_ADMIN_CLIENT_SECRET="backend-secret",
        KEYCLOAK_TOKEN_TIMEOUT=7,
    )
    @patch("common.keycloak_admin.requests.post")
    def test_refresh_keycloak_token_uses_backend_client(self, mock_post):
        mock_post.return_value = _Response(
            200,
            {
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_in": 300,
                "refresh_expires_in": 1800,
            },
        )

        token_data = refresh_keycloak_token("old-refresh-token")

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["data"]["grant_type"], "refresh_token")
        self.assertEqual(kwargs["data"]["client_id"], "backend-client")
        self.assertEqual(kwargs["data"]["client_secret"], "backend-secret")
        self.assertEqual(kwargs["data"]["refresh_token"], "old-refresh-token")
        self.assertEqual(kwargs["timeout"], 7)
        self.assertEqual(token_data["access_token"], "new-access-token")


class MobileLogoutViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("apps.users.auth_views.logout_keycloak_refresh_token")
    def test_mobile_logout_revokes_refresh_token(self, mock_logout):
        response = self.client.post(
            reverse("users:mobile-logout"),
            {"refresh_token": "refresh-token"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        mock_logout.assert_called_once_with("refresh-token")


class MobileTokenRefreshViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("apps.users.auth_views.refresh_keycloak_token")
    def test_mobile_refresh_returns_new_tokens(self, mock_refresh):
        mock_refresh.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "token_type": "Bearer",
            "expires_in": 300,
            "refresh_expires_in": 1800,
        }

        response = self.client.post(
            reverse("users:mobile-token-refresh"),
            {"refresh_token": "old-refresh-token"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["access_token"], "new-access-token")
        self.assertEqual(response.data["data"]["refresh_token"], "new-refresh-token")
        mock_refresh.assert_called_once_with("old-refresh-token")

    @patch("apps.users.auth_views.refresh_keycloak_token")
    def test_mobile_refresh_rejects_invalid_refresh_token(self, mock_refresh):
        mock_refresh.side_effect = KeycloakAdminError(
            "invalid refresh", status_code=400
        )

        response = self.client.post(
            reverse("users:mobile-token-refresh"),
            {"refresh_token": "old-refresh-token"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], "invalid_credentials")


@override_settings(OTP_TTL_SECONDS=180, OTP_MAX_ATTEMPTS=3)
class OtpVerifyViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.email = "test@st.utc2.edu.vn"
        cache.delete(otp_service._key_code(self.email))
        cache.delete(otp_service._key_attempts(self.email))
        cache.delete(otp_service._key_cooldown(self.email))

    def _seed_otp(self):
        cache.set(otp_service._key_code(self.email), "123456", timeout=180)
        cache.set(otp_service._key_attempts(self.email), 0, timeout=180)
        cache.set(otp_service._key_cooldown(self.email), "1", timeout=60)

    @patch("apps.users.otp_views.exchange_token_for_user")
    @patch("apps.users.otp_views.get_or_create_keycloak_user")
    def test_verify_keeps_otp_when_keycloak_token_exchange_fails(
        self,
        mock_get_or_create_user,
        mock_exchange_token,
    ):
        self._seed_otp()
        mock_get_or_create_user.return_value = "keycloak-user-id"
        mock_exchange_token.side_effect = KeycloakAdminError("token exchange down")

        response = self.client.post(
            reverse("users:otp-verify"),
            {"email": self.email, "code": "123456"},
            format="json",
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(cache.get(otp_service._key_code(self.email)), "123456")

    @patch("apps.users.otp_views.KeycloakJWTAuthentication.authenticate_token")
    @patch("apps.users.otp_views.exchange_token_for_user")
    @patch("apps.users.otp_views.get_or_create_keycloak_user")
    def test_verify_consumes_otp_after_successful_token_login(
        self,
        mock_get_or_create_user,
        mock_exchange_token,
        mock_authenticate_token,
    ):
        self._seed_otp()
        mock_get_or_create_user.return_value = "keycloak-user-id"
        mock_exchange_token.return_value = {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "token_type": "Bearer",
            "expires_in": 300,
            "refresh_expires_in": 1800,
        }
        mock_authenticate_token.return_value = (object(), {"sub": "keycloak-user-id"})

        response = self.client.post(
            reverse("users:otp-verify"),
            {"email": self.email, "code": "123456"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(cache.get(otp_service._key_code(self.email)))


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

    @override_settings(
        GOOGLE_OAUTH_CLIENT_IDS=["google-web-client-id"],
        GOOGLE_TOKEN_AUTH_RETRY_DELAY_SECONDS=0,
    )
    @patch("apps.users.google_views.KeycloakJWTAuthentication.authenticate_token")
    @patch("apps.users.google_views.exchange_token_for_user")
    @patch("apps.users.google_views.get_or_create_keycloak_user")
    @patch("apps.users.google_views.google_id_token.verify_oauth2_token")
    def test_google_verify_retries_when_exchanged_token_is_not_ready(
        self,
        mock_verify_google,
        mock_get_or_create_user,
        mock_exchange_token,
        mock_authenticate_token,
    ):
        mock_verify_google.return_value = {
            "sub": "google-subject",
            "email": "test@st.utc2.edu.vn",
            "email_verified": True,
        }
        mock_get_or_create_user.return_value = "keycloak-user-id"
        mock_exchange_token.side_effect = [
            {
                "access_token": "first-access-token",
                "refresh_token": "first-refresh-token",
                "token_type": "Bearer",
                "expires_in": 300,
                "refresh_expires_in": 1800,
            },
            {
                "access_token": "second-access-token",
                "refresh_token": "second-refresh-token",
                "token_type": "Bearer",
                "expires_in": 300,
                "refresh_expires_in": 1800,
            },
        ]
        mock_authenticate_token.side_effect = [
            AuthenticationFailed("Token missing email."),
            (self.user, {"sub": "keycloak-user-id"}),
        ]

        response = self.client.post(
            reverse("users:google-verify"),
            {"id_token": "google-id-token"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["access_token"], "second-access-token")
        self.assertEqual(mock_exchange_token.call_count, 2)
        self.assertEqual(mock_authenticate_token.call_count, 2)

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
        self.assertTrue(
            UserRole.objects.filter(user=user, role=self.student_role).exists()
        )
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
