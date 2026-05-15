from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.system_admin.models import ExportJob
from apps.system_admin.services.user_export_service import AdminUserExportService
from apps.users.models import Role, UserRole
from common.response_codes import ResponseCode
from common.responses import build_api_response


class AdminApiResponseContractTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_password = "AdminPass123!"
        cls.admin_user = user_model.objects.create_user(
            username="admin_contrac",
            email="admin_contract@example.com",
            password=cls.admin_password,
            full_name="Admin Contract",
            is_staff=True,
            is_superuser=True,
        )
        cls.target_user = user_model.objects.create_user(
            username="target_contract",
            email="target_contract@example.com",
            password="TargetPass123!",
            full_name="Target Contract",
            is_staff=False,
            is_superuser=False,
        )
        cls.role = Role.objects.create(
            code="contract_role",
            name="Contract Role",
            description="Role dùng cho test API response contract.",
        )
        UserRole.objects.create(
            user=cls.target_user,
            role=cls.role,
            assigned_by=cls.admin_user,
            is_primary=True,
        )

    def setUp(self):
        self.client = APIClient()

    def authenticate_admin(self):
        self.client.force_authenticate(user=self.admin_user)

    def assert_success_envelope(
        self,
        response,
        *,
        expected_status=200,
        expected_code=ResponseCode.SUCCESS.value,
        expected_message=None,
        data_type=None,
    ):
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(set(response.data.keys()), {"success", "code", "message", "data", "errors", "meta"})
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["code"], expected_code)
        if expected_message is not None:
            self.assertEqual(response.data["message"], expected_message)
        self.assertIsNone(response.data["errors"])
        self.assertIsInstance(response.data["meta"], dict)
        if data_type is not None:
            self.assertIsInstance(response.data["data"], data_type)

    def assert_error_envelope(self, response, *, expected_status, expected_code=None):
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(set(response.data.keys()), {"success", "code", "message", "data", "errors", "meta"})
        self.assertFalse(response.data["success"])
        if expected_code is not None:
            self.assertEqual(response.data["code"], expected_code)
        self.assertIsNone(response.data["data"])
        self.assertIn("message", response.data)
        self.assertIsInstance(response.data["meta"], dict)

    def test_admin_envelope_uses_response_code_enum_value(self):
        response = build_api_response(
            success=False,
            code=ResponseCode.INVALID_AUDIT_FILTER,
            errors={"filter": ["Unsupported filter."]},
        )

        self.assertFalse(response["success"])
        self.assertEqual(response["code"], "invalid_audit_filter")
        self.assertIsNone(response["data"])
        self.assertEqual(response["errors"], {"filter": ["Unsupported filter."]})

    def test_admin_user_list_success_uses_paginated_response_envelope(self):
        self.authenticate_admin()

        response = self.client.get(reverse("system_admin:user-list"))

        self.assert_success_envelope(
            response,
            expected_message="Lấy danh sách dữ liệu thành công.",
            data_type=list,
        )
        self.assertIn("pagination", response.data["meta"])
        self.assertIn("count", response.data["meta"]["pagination"])
        self.assertIn("page", response.data["meta"]["pagination"])
        self.assertIn("page_size", response.data["meta"]["pagination"])
        self.assertIn("total_pages", response.data["meta"]["pagination"])

    def test_admin_create_user_success_uses_created_response_envelope(self):
        self.authenticate_admin()

        response = self.client.post(
            reverse("system_admin:user-list"),
            {
                "username": "created_contract",
                "email": "created_contract@example.com",
                "password": "CreatedPass123!",
                "full_name": "Created Contract",
                "student_code": "SC_CREATED_001",
                "phone_number": "0900000001",
                "faculty": "Engineering",
                "class_name": "ENG01",
                "role_codes": [self.role.code],
            },
            format="json",
        )

        self.assert_success_envelope(
            response,
            expected_status=201,
            expected_code=ResponseCode.CREATED.value,
            expected_message="Tạo người dùng thành công.",
            data_type=dict,
        )
        self.assertEqual(response.data["data"]["username"], "created_contract")
        self.assertEqual(response.data["data"]["email"], "created_contract@example.com")
        self.assertEqual(response.data["data"]["student_code"], "SC_CREATED_001")
        self.assertEqual(response.data["data"]["user_roles"][0]["role"]["code"], self.role.code)

    def test_admin_create_user_legacy_route_still_uses_created_response_envelope(self):
        self.authenticate_admin()

        response = self.client.post(
            reverse("system_admin:user-create"),
            {
                "username": "legacy_created_contract",
                "email": "legacy_created_contract@example.com",
                "password": "CreatedPass123!",
                "full_name": "Legacy Created Contract",
            },
            format="json",
        )

        self.assert_success_envelope(
            response,
            expected_status=201,
            expected_code=ResponseCode.CREATED.value,
            expected_message="Tạo người dùng thành công.",
            data_type=dict,
        )
        self.assertEqual(response.data["data"]["username"], "legacy_created_contract")

    def test_admin_create_user_duplicate_username_uses_error_envelope(self):
        self.authenticate_admin()

        response = self.client.post(
            reverse("system_admin:user-create"),
            {
                "username": self.target_user.username,
                "email": "duplicate_username@example.com",
                "password": "CreatedPass123!",
            },
            format="json",
        )

        self.assert_error_envelope(
            response,
            expected_status=400,
            expected_code=ResponseCode.API_ERROR.value,
        )
        self.assertIn("username", response.data["errors"])

    def test_admin_create_user_invalid_role_uses_error_envelope(self):
        self.authenticate_admin()

        response = self.client.post(
            reverse("system_admin:user-create"),
            {
                "username": "invalid_role_contract",
                "email": "invalid_role_contract@example.com",
                "password": "CreatedPass123!",
                "role_codes": ["missing_contract_role"],
            },
            format="json",
        )

        self.assert_error_envelope(
            response,
            expected_status=404,
            expected_code=ResponseCode.NOT_FOUND.value,
        )

    def test_admin_create_user_non_admin_uses_error_envelope(self):
        self.client.force_authenticate(user=self.target_user)

        response = self.client.post(
            reverse("system_admin:user-list"),
            {
                "username": "forbidden_created_contract",
                "email": "forbidden_created_contract@example.com",
                "password": "CreatedPass123!",
            },
            format="json",
        )

        self.assert_error_envelope(
            response,
            expected_status=403,
            expected_code=ResponseCode.FORBIDDEN.value,
        )

    def test_admin_user_list_anonymous_uses_error_envelope(self):
        response = self.client.get(reverse("system_admin:user-list"))

        self.assert_error_envelope(
            response,
            expected_status=401,
            expected_code=ResponseCode.UNAUTHORIZED.value,
        )

    def test_admin_user_detail_non_admin_uses_error_envelope(self):
        self.client.force_authenticate(user=self.target_user)

        response = self.client.get(reverse("system_admin:user-detail", kwargs={"pk": self.target_user.pk}))

        self.assert_error_envelope(
            response,
            expected_status=403,
            expected_code=ResponseCode.FORBIDDEN.value,
        )

    def test_admin_user_detail_success_uses_shared_response_envelope(self):
        self.authenticate_admin()

        response = self.client.get(reverse("system_admin:user-detail", kwargs={"pk": self.target_user.pk}))

        self.assert_success_envelope(
            response,
            expected_message="Lấy thông tin người dùng thành công.",
            data_type=dict,
        )
        self.assertEqual(response.data["data"]["username"], self.target_user.username)

    def test_admin_user_patch_success_uses_shared_response_envelope(self):
        self.authenticate_admin()

        response = self.client.patch(
            reverse("system_admin:user-detail", kwargs={"pk": self.target_user.pk}),
            {"full_name": "Target Contract Updated"},
            format="json",
        )

        self.assert_success_envelope(
            response,
            expected_message="Cập nhật người dùng thành công.",
            data_type=dict,
        )
        self.assertEqual(response.data["data"]["full_name"], "Target Contract Updated")

    def test_admin_user_delete_success_uses_shared_response_envelope(self):
        self.authenticate_admin()
        user_model = get_user_model()
        deletable_user = user_model.objects.create_user(
            username="deletable_contract",
            email="deletable_contract@example.com",
            password="DeletePass123!",
        )

        response = self.client.delete(
            reverse("system_admin:user-detail", kwargs={"pk": deletable_user.pk}),
            {"reason": "Test contract envelope."},
            format="json",
        )

        self.assert_success_envelope(
            response,
            expected_code=ResponseCode.DELETED.value,
            expected_message="Xóa mềm người dùng thành công.",
        )
        self.assertIsNone(response.data["data"])

    def test_admin_ban_user_success_uses_shared_response_envelope(self):
        self.authenticate_admin()

        response = self.client.post(
            reverse("system_admin:user-ban", kwargs={"pk": self.target_user.pk}),
            {"reason": "Test ban envelope."},
            format="json",
        )

        self.assert_success_envelope(
            response,
            expected_message="Khóa người dùng thành công.",
            data_type=dict,
        )
        self.assertEqual(response.data["data"]["account_status"], "banned")

    def test_admin_unban_user_success_uses_shared_response_envelope(self):
        self.authenticate_admin()
        self.target_user.account_status = "banned"
        self.target_user.save(update_fields=["account_status", "updated_at"])

        response = self.client.post(
            reverse("system_admin:user-unban", kwargs={"pk": self.target_user.pk}),
            {"reason": "Test unban envelope."},
            format="json",
        )

        self.assert_success_envelope(
            response,
            expected_message="Mở khóa người dùng thành công.",
            data_type=dict,
        )
        self.assertEqual(response.data["data"]["account_status"], "active")

    def test_admin_restore_user_success_uses_shared_response_envelope(self):
        self.authenticate_admin()
        user_model = get_user_model()
        restorable_user = user_model.objects.create_user(
            username="restorable_contract",
            email="restorable_contract@example.com",
            password="RestorePass123!",
        )
        restorable_user.delete()

        response = self.client.post(reverse("system_admin:user-restore", kwargs={"pk": restorable_user.pk}))

        self.assert_success_envelope(
            response,
            expected_message="Khôi phục người dùng thành công.",
            data_type=dict,
        )
        self.assertEqual(response.data["data"]["username"], restorable_user.username)

    def test_admin_assign_role_success_uses_shared_response_envelope(self):
        self.authenticate_admin()
        role = Role.objects.create(
            code="assign_contract_role",
            name="Assign Contract Role",
            description="Role dùng cho test gán role.",
        )

        response = self.client.post(
            reverse("system_admin:user-roles", kwargs={"pk": self.target_user.pk}),
            {"role_code": role.code},
            format="json",
        )

        self.assert_success_envelope(
            response,
            expected_message="Gán vai trò người dùng thành công.",
            data_type=dict,
        )
        role_codes = [item["role"]["code"] for item in response.data["data"]["user_roles"]]
        self.assertIn(role.code, role_codes)

    def test_admin_remove_role_success_uses_shared_response_envelope(self):
        self.authenticate_admin()
        removable_role = Role.objects.create(
            code="remove_contract_role",
            name="Remove Contract Role",
            description="Role dùng cho test gỡ role.",
        )
        UserRole.objects.create(
            user=self.target_user,
            role=removable_role,
            assigned_by=self.admin_user,
            is_primary=False,
        )

        response = self.client.delete(
            reverse(
                "system_admin:user-role-remove",
                kwargs={"pk": self.target_user.pk, "role_code": removable_role.code},
            ),
        )

        self.assert_success_envelope(
            response,
            expected_message="Gỡ vai trò người dùng thành công.",
            data_type=dict,
        )
        role_codes = [item["role"]["code"] for item in response.data["data"]["user_roles"]]
        self.assertNotIn(removable_role.code, role_codes)

    def test_admin_remove_primary_role_uses_error_envelope(self):
        self.authenticate_admin()

        response = self.client.delete(
            reverse(
                "system_admin:user-role-remove",
                kwargs={"pk": self.target_user.pk, "role_code": self.role.code},
            ),
        )

        self.assert_error_envelope(
            response,
            expected_status=400,
            expected_code=ResponseCode.VALIDATION_ERROR.value,
        )

    def test_admin_user_export_create_success_uses_accepted_response_envelope(self):
        self.authenticate_admin()

        response = self.client.post(
            reverse("system_admin:user-export"),
            {
                "format": "csv",
                "filters": {"account_status": "active"},
                "fields": ["id", "username", "email", "account_status"],
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY="export-contract-key-1",
        )

        self.assert_success_envelope(
            response,
            expected_status=202,
            expected_code=ResponseCode.ACCEPTED.value,
            expected_message="Tạo job export người dùng thành công.",
            data_type=dict,
        )
        self.assertEqual(response.data["data"]["status"], ExportJob.Status.PENDING)
        self.assertEqual(response.data["data"]["format"], ExportJob.ExportFormat.CSV)
        self.assertIn("job_id", response.data["data"])
        self.assertTrue(
            ExportJob.objects.filter(
                actor=self.admin_user,
                idempotency_key="export-contract-key-1",
            ).exists()
        )

    def test_admin_user_export_create_xlsx_processes_with_xlsx_file_key(self):
        self.authenticate_admin()

        response = self.client.post(
            reverse("system_admin:user-export"),
            {
                "format": "xlsx",
                "filters": {"account_status": "active"},
                "fields": ["id", "username", "email", "account_status"],
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY="export-contract-key-xlsx",
        )

        self.assert_success_envelope(
            response,
            expected_status=202,
            expected_code=ResponseCode.ACCEPTED.value,
            expected_message="Tạo job export người dùng thành công.",
            data_type=dict,
        )
        self.assertEqual(response.data["data"]["format"], ExportJob.ExportFormat.XLSX)

        job = AdminUserExportService.process_user_export_job(
            job_id=response.data["data"]["job_id"],
        )

        self.assertEqual(job.status, ExportJob.Status.COMPLETED)
        self.assertTrue(job.file_key.endswith(".xlsx"))
        self.assertGreater(job.file_size_bytes, 0)
        self.assertEqual(job.rows_count, 2)

    def test_admin_user_export_reuses_idempotency_key(self):
        self.authenticate_admin()
        payload = {"format": "csv", "filters": {"faculty": "Engineering"}}

        first_response = self.client.post(
            reverse("system_admin:user-export"),
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY="export-contract-key-2",
        )
        second_response = self.client.post(
            reverse("system_admin:user-export"),
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY="export-contract-key-2",
        )

        self.assert_success_envelope(
            second_response,
            expected_status=202,
            expected_code=ResponseCode.ACCEPTED.value,
            expected_message="Job export người dùng đã tồn tại.",
            data_type=dict,
        )
        self.assertEqual(first_response.data["data"]["job_id"], second_response.data["data"]["job_id"])
        self.assertEqual(ExportJob.objects.filter(idempotency_key="export-contract-key-2").count(), 1)

    def test_admin_user_export_conflicting_idempotency_key_uses_error_envelope(self):
        self.authenticate_admin()

        self.client.post(
            reverse("system_admin:user-export"),
            {"format": "csv", "filters": {"faculty": "Engineering"}},
            format="json",
            HTTP_IDEMPOTENCY_KEY="export-contract-key-3",
        )
        response = self.client.post(
            reverse("system_admin:user-export"),
            {"format": "csv", "filters": {"faculty": "Business"}},
            format="json",
            HTTP_IDEMPOTENCY_KEY="export-contract-key-3",
        )

        self.assert_error_envelope(
            response,
            expected_status=409,
            expected_code=ResponseCode.CONFLICT.value,
        )

    def test_admin_user_export_missing_idempotency_key_uses_error_envelope(self):
        self.authenticate_admin()

        response = self.client.post(
            reverse("system_admin:user-export"),
            {"format": "csv"},
            format="json",
        )

        self.assert_error_envelope(
            response,
            expected_status=400,
            expected_code=ResponseCode.VALIDATION_ERROR.value,
        )

    def test_admin_user_export_invalid_filter_uses_error_envelope(self):
        self.authenticate_admin()

        response = self.client.post(
            reverse("system_admin:user-export"),
            {"filters": {"password": "secret"}},
            format="json",
            HTTP_IDEMPOTENCY_KEY="export-contract-key-4",
        )

        self.assert_error_envelope(
            response,
            expected_status=400,
            expected_code=ResponseCode.API_ERROR.value,
        )
        self.assertIn("filters", response.data["errors"])

    def test_admin_user_export_download_success_returns_csv(self):
        self.authenticate_admin()

        response = self.client.get(
            reverse("system_admin:user-export"),
            {"fields": ["username", "email"], "search": self.target_user.username},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment; filename=", response["Content-Disposition"])
        csv_content = response.content.decode("utf-8")
        self.assertIn("username,email", csv_content)
        self.assertIn(self.target_user.username, csv_content)
        self.assertIn(self.target_user.email, csv_content)

    def test_admin_user_export_download_success_returns_xlsx(self):
        self.authenticate_admin()

        response = self.client.get(
            reverse("system_admin:user-export"),
            {"export_format": "xlsx", "fields": ["username", "email"], "search": self.target_user.username},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn("attachment; filename=", response["Content-Disposition"])
        self.assertTrue(response["Content-Disposition"].endswith('.xlsx"'))
        self.assertTrue(response.content.startswith(b"PK"))

    def test_admin_user_export_download_non_admin_uses_error_envelope(self):
        self.client.force_authenticate(user=self.target_user)

        response = self.client.get(reverse("system_admin:user-export"))

        self.assert_error_envelope(
            response,
            expected_status=403,
            expected_code=ResponseCode.FORBIDDEN.value,
        )

    def test_admin_export_job_detail_success_uses_shared_response_envelope(self):
        self.authenticate_admin()
        create_response = self.client.post(
            reverse("system_admin:user-export"),
            {"format": "csv"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="export-contract-key-5",
        )
        job_id = create_response.data["data"]["job_id"]

        response = self.client.get(reverse("system_admin:export-job-detail", kwargs={"job_id": job_id}))

        self.assert_success_envelope(
            response,
            expected_message="Lấy trạng thái job export thành công.",
            data_type=dict,
        )
        self.assertEqual(response.data["data"]["job_id"], job_id)

    def test_admin_export_job_detail_not_found_uses_error_envelope(self):
        self.authenticate_admin()

        response = self.client.get(
            reverse("system_admin:export-job-detail", kwargs={"job_id": "00000000-0000-0000-0000-000000000000"})
        )

        self.assert_error_envelope(
            response,
            expected_status=404,
            expected_code=ResponseCode.NOT_FOUND.value,
        )

    def test_admin_user_export_non_admin_uses_error_envelope(self):
        self.client.force_authenticate(user=self.target_user)

        response = self.client.post(
            reverse("system_admin:user-export"),
            {"format": "csv"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="export-contract-key-6",
        )

        self.assert_error_envelope(
            response,
            expected_status=403,
            expected_code=ResponseCode.FORBIDDEN.value,
        )

    def test_admin_user_statistics_success_uses_shared_response_envelope(self):
        self.authenticate_admin()

        response = self.client.get(reverse("system_admin:user-statistics"))

        self.assert_success_envelope(
            response,
            expected_message="Lấy thống kê người dùng thành công.",
            data_type=dict,
        )
        self.assertIn("total_users", response.data["data"])
        self.assertIn("by_status", response.data["data"])
