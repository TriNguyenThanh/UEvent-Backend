from django.test import SimpleTestCase

from common.response_codes import ResponseCode
from common.responses import success_response


class AdminResponseEnvelopeTests(SimpleTestCase):
    def test_success_response_includes_empty_meta_by_default(self):
        response = success_response(data=[{"id": "1"}], code=ResponseCode.SUCCESS)

        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["code"], "success")
        self.assertEqual(response.data["data"], [{"id": "1"}])
        self.assertIsNone(response.data["errors"])
        self.assertEqual(response.data["meta"], {})
