from django.test import SimpleTestCase

from common.response_codes import ResponseCode
from common.responses import build_api_response


class SystemAdminResponseContractTests(SimpleTestCase):
    def test_build_api_response_serializes_response_code_value(self):
        payload = build_api_response(
            success=True,
            code=ResponseCode.SUCCESS,
            data={"ok": True},
            request_id="req-admin",
        )

        self.assertEqual(payload["code"], "success")
        self.assertEqual(payload["data"], {"ok": True})
        self.assertEqual(payload["errors"], None)
        self.assertEqual(payload["meta"]["request_id"], "req-admin")
