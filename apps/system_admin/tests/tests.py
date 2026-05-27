from django.test import SimpleTestCase

from apps.system_admin.services.audit_service import AdminAuditService
from apps.system_admin.services.csv_export_service import AdminCsvExportService
from apps.system_admin.services.openobserve_audit_client import OpenObserveAuditClient
from common.exceptions import ValidationError


class AdminPhase0FoundationTests(SimpleTestCase):
    def test_audit_service_masks_sensitive_data(self):
        payload = {
            "username": "admin",
            "password": "secret",
            "nested": {"authorization": "Bearer token"},
            "items": [{"refresh_token": "refresh"}],
        }

        sanitized = AdminAuditService.mask_sensitive_data(payload)

        self.assertEqual(sanitized["username"], "admin")
        self.assertEqual(sanitized["password"], AdminAuditService.MASK_VALUE)
        self.assertEqual(sanitized["nested"]["authorization"], AdminAuditService.MASK_VALUE)
        self.assertEqual(sanitized["items"][0]["refresh_token"], AdminAuditService.MASK_VALUE)

    def test_csv_export_response_has_content_disposition(self):
        response = AdminCsvExportService.build_response(
            filename="users.csv",
            headers=["id", "email"],
            rows=[{"id": "1", "email": "admin@test.com"}],
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="users.csv"')
        self.assertIn("id,email", response.content.decode("utf-8"))

    def test_openobserve_client_rejects_unknown_filters(self):
        with self.assertRaises(ValidationError):
            OpenObserveAuditClient._validate_filters({"password": "secret"})
