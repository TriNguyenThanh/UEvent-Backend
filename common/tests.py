from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework import status

from common import otp
from common.response_codes import ResponseCode
from common.responses import error_response, success_response


class ApiResponseContractTests(SimpleTestCase):
    def test_success_response_uses_shared_envelope_and_response_code(self):
        response = success_response(
            data={"id": "1"}, code=ResponseCode.SUCCESS, request_id="req-1"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["code"], "success")
        self.assertEqual(response.data["data"], {"id": "1"})
        self.assertIsNone(response.data["errors"])
        self.assertEqual(response.data["meta"]["request_id"], "req-1")

    def test_error_response_uses_shared_envelope_and_response_code(self):
        response = error_response(
            code=ResponseCode.VALIDATION_ERROR,
            errors={"email": ["Invalid email."]},
            request_id="req-2",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["code"], "validation_error")
        self.assertIsNone(response.data["data"])
        self.assertEqual(response.data["errors"], {"email": ["Invalid email."]})
        self.assertEqual(response.data["meta"]["request_id"], "req-2")


@override_settings(OTP_TTL_SECONDS=180, OTP_MAX_ATTEMPTS=3)
class OtpServiceTests(TestCase):
    def setUp(self):
        self.email = "test@st.utc2.edu.vn"
        cache.delete(otp._key_code(self.email))
        cache.delete(otp._key_attempts(self.email))
        cache.delete(otp._key_cooldown(self.email))

    def test_verify_otp_can_validate_without_consuming_code(self):
        cache.set(otp._key_code(self.email), "123456", timeout=180)
        cache.set(otp._key_attempts(self.email), 0, timeout=180)
        cache.set(otp._key_cooldown(self.email), "1", timeout=60)

        otp.verify_otp(self.email, "123456", consume=False)

        self.assertEqual(cache.get(otp._key_code(self.email)), "123456")
        otp.consume_otp(self.email)
        self.assertIsNone(cache.get(otp._key_code(self.email)))

    def test_verify_otp_consumes_code_by_default(self):
        cache.set(otp._key_code(self.email), "123456", timeout=180)
        cache.set(otp._key_attempts(self.email), 0, timeout=180)

        otp.verify_otp(self.email, "123456")

        self.assertIsNone(cache.get(otp._key_code(self.email)))
