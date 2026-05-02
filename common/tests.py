from django.test import SimpleTestCase
from rest_framework import status

from common.response_codes import ResponseCode
from common.responses import error_response, success_response


class ApiResponseContractTests(SimpleTestCase):
    def test_success_response_uses_shared_envelope_and_response_code(self):
        response = success_response(data={"id": "1"}, code=ResponseCode.SUCCESS, request_id="req-1")

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
