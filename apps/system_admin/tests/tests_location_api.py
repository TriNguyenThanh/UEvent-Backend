from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.events.models import Event, EventCategory
from apps.locations.models import Building, Campus, Room
from common.response_codes import ResponseCode


class AdminLocationApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_user(
            username="location_admin",
            email="location_admin@example.com",
            password="AdminPass123!",
            is_staff=True,
            is_superuser=True,
        )
        cls.regular_user = user_model.objects.create_user(
            username="location_user",
            email="location_user@example.com",
            password="UserPass123!",
        )
        cls.campus = Campus.objects.create(
            name="Cơ sở Thủ Đức",
            code="TD",
            address="Thành phố Thủ Đức",
        )
        cls.building = Building.objects.create(
            campus=cls.campus,
            name="Tòa A",
            code="A",
        )
        cls.room = Room.objects.create(
            building=cls.building,
            name="Hội trường A1",
            code="A1",
            capacity=300,
        )
        cls.category = EventCategory.objects.create(
            name="Hội thảo địa điểm",
            slug="hoi-thao-dia-diem",
        )
        now = timezone.now()
        cls.event = Event.objects.create(
            category=cls.category,
            room=cls.room,
            created_by=cls.regular_user,
            title="Sự kiện tại A1",
            slug="su-kien-tai-a1",
            description="Sự kiện dùng để kiểm tra liên kết địa điểm.",
            status=Event.Status.APPROVED,
            visibility=Event.Visibility.PUBLIC,
            registration_open_at=now - timedelta(days=1),
            registration_close_at=now + timedelta(days=1),
            start_at=now + timedelta(days=3),
            end_at=now + timedelta(days=3, hours=2),
            max_capacity=100,
            location_snapshot="Hội trường A1, Tòa A, Cơ sở Thủ Đức",
        )

    def setUp(self):
        self.client = APIClient()

    def authenticate_admin(self):
        self.client.force_authenticate(user=self.admin_user)

    def assert_success_envelope(self, response, *, expected_status=200, expected_code=ResponseCode.SUCCESS.value):
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(set(response.data.keys()), {"success", "code", "message", "data", "errors", "meta"})
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["code"], expected_code)
        self.assertIsNone(response.data["errors"])

    def assert_error_envelope(self, response, *, expected_status, expected_code=None):
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(set(response.data.keys()), {"success", "code", "message", "data", "errors", "meta"})
        self.assertFalse(response.data["success"])
        if expected_code is not None:
            self.assertEqual(response.data["code"], expected_code)

    def test_location_admin_permission_required(self):
        response = self.client.get(reverse("system_admin:location-campus-list"))
        self.assert_error_envelope(
            response,
            expected_status=401,
            expected_code=ResponseCode.UNAUTHORIZED.value,
        )

        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(reverse("system_admin:location-campus-list"))
        self.assert_error_envelope(
            response,
            expected_status=403,
            expected_code=ResponseCode.FORBIDDEN.value,
        )

    def test_campus_list_create_update_and_statistics(self):
        self.authenticate_admin()

        list_response = self.client.get(reverse("system_admin:location-campus-list"))
        self.assert_success_envelope(list_response)
        self.assertIn("pagination", list_response.data["meta"])
        self.assertEqual(list_response.data["data"][0]["building_count"], 1)
        self.assertEqual(list_response.data["data"][0]["room_count"], 1)
        self.assertEqual(list_response.data["data"][0]["event_count"], 1)

        create_response = self.client.post(
            reverse("system_admin:location-campus-list"),
            {
                "name": "Cơ sở Quận 1",
                "code": "q1",
                "address": "Quận 1, TP. Hồ Chí Minh",
                "is_active": True,
            },
            format="json",
        )
        self.assert_success_envelope(
            create_response,
            expected_status=201,
            expected_code=ResponseCode.CREATED.value,
        )
        campus_id = create_response.data["data"]["id"]
        self.assertEqual(create_response.data["data"]["code"], "Q1")

        update_response = self.client.patch(
            reverse("system_admin:location-campus-detail", kwargs={"pk": campus_id}),
            {"address": "Quận 1, Thành phố Hồ Chí Minh", "is_active": False},
            format="json",
        )
        self.assert_success_envelope(update_response)
        self.assertFalse(update_response.data["data"]["is_active"])

        stats_response = self.client.get(reverse("system_admin:location-statistics"))
        self.assert_success_envelope(stats_response)
        self.assertIn("total_campuses", stats_response.data["data"])
        self.assertIn("total_capacity", stats_response.data["data"])

    def test_duplicate_campus_code_returns_validation_error(self):
        self.authenticate_admin()

        response = self.client.post(
            reverse("system_admin:location-campus-list"),
            {"name": "Cơ sở trùng mã", "code": self.campus.code},
            format="json",
        )

        self.assert_error_envelope(
            response,
            expected_status=400,
            expected_code=ResponseCode.API_ERROR.value,
        )
        self.assertIn("code", response.data["errors"])

    def test_building_crud_filters_and_duplicate_code_validation(self):
        self.authenticate_admin()

        create_response = self.client.post(
            reverse("system_admin:location-building-list"),
            {
                "campus_id": str(self.campus.id),
                "name": "Tòa B",
                "code": "b",
                "is_active": True,
            },
            format="json",
        )
        self.assert_success_envelope(
            create_response,
            expected_status=201,
            expected_code=ResponseCode.CREATED.value,
        )
        building_id = create_response.data["data"]["id"]
        self.assertEqual(create_response.data["data"]["code"], "B")

        list_response = self.client.get(
            reverse("system_admin:location-building-list"),
            {"campus": str(self.campus.id), "search": "B"},
        )
        self.assert_success_envelope(list_response)
        self.assertEqual(list_response.data["meta"]["pagination"]["count"], 1)

        duplicate_response = self.client.post(
            reverse("system_admin:location-building-list"),
            {
                "campus_id": str(self.campus.id),
                "name": "Tòa trùng",
                "code": "B",
            },
            format="json",
        )
        self.assert_error_envelope(duplicate_response, expected_status=400, expected_code=ResponseCode.API_ERROR.value)
        self.assertIn("code", duplicate_response.data["errors"])

        update_response = self.client.patch(
            reverse("system_admin:location-building-detail", kwargs={"pk": building_id}),
            {"name": "Tòa B mới"},
            format="json",
        )
        self.assert_success_envelope(update_response)
        self.assertEqual(update_response.data["data"]["name"], "Tòa B mới")

    def test_room_crud_filters_capacity_validation_and_delete_strategy(self):
        self.authenticate_admin()
        empty_room = Room.objects.create(
            building=self.building,
            name="Phòng chưa dùng",
            code="EMPTY",
        )

        create_response = self.client.post(
            reverse("system_admin:location-room-list"),
            {
                "building_id": str(self.building.id),
                "name": "Phòng B1",
                "code": "b1",
                "capacity": 80,
                "is_active": True,
            },
            format="json",
        )
        self.assert_success_envelope(
            create_response,
            expected_status=201,
            expected_code=ResponseCode.CREATED.value,
        )
        room_id = create_response.data["data"]["id"]
        self.assertEqual(create_response.data["data"]["code"], "B1")

        invalid_response = self.client.post(
            reverse("system_admin:location-room-list"),
            {
                "building_id": str(self.building.id),
                "name": "Phòng lỗi",
                "code": "ERR",
                "capacity": 0,
            },
            format="json",
        )
        self.assert_error_envelope(invalid_response, expected_status=400, expected_code=ResponseCode.API_ERROR.value)
        self.assertIn("capacity", invalid_response.data["errors"])

        list_response = self.client.get(
            reverse("system_admin:location-room-list"),
            {"campus": str(self.campus.id), "building": str(self.building.id), "search": "b1"},
        )
        self.assert_success_envelope(list_response)
        self.assertEqual(list_response.data["meta"]["pagination"]["count"], 1)

        update_response = self.client.patch(
            reverse("system_admin:location-room-detail", kwargs={"pk": room_id}),
            {"capacity": 100},
            format="json",
        )
        self.assert_success_envelope(update_response)
        self.assertEqual(update_response.data["data"]["capacity"], 100)

        delete_empty_response = self.client.delete(
            reverse("system_admin:location-room-detail", kwargs={"pk": empty_room.pk}),
        )
        self.assert_success_envelope(delete_empty_response, expected_code=ResponseCode.DELETED.value)
        self.assertFalse(Room.objects.filter(pk=empty_room.pk).exists())
        self.assertIsNotNone(Room.all_objects.get(pk=empty_room.pk).deleted_at)

        delete_linked_response = self.client.delete(
            reverse("system_admin:location-room-detail", kwargs={"pk": self.room.pk}),
            {"reason": "Không nhận sự kiện mới."},
            format="json",
        )
        self.assert_success_envelope(delete_linked_response, expected_code=ResponseCode.DELETED.value)
        self.room.refresh_from_db()
        self.assertFalse(self.room.is_active)
        self.assertIsNone(self.room.deleted_at)

    def test_deleting_linked_campus_deactivates_children(self):
        self.authenticate_admin()

        response = self.client.delete(
            reverse("system_admin:location-campus-detail", kwargs={"pk": self.campus.pk}),
            {"reason": "Tạm dừng khai thác cơ sở."},
            format="json",
        )

        self.assert_success_envelope(response, expected_code=ResponseCode.DELETED.value)
        self.campus.refresh_from_db()
        self.building.refresh_from_db()
        self.room.refresh_from_db()
        self.assertFalse(self.campus.is_active)
        self.assertFalse(self.building.is_active)
        self.assertFalse(self.room.is_active)
