from rest_framework import status
from rest_framework.test import APITestCase

from apps.locations.models import Building, Campus, Room
from apps.users.models import User


class RoomListViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="organizer", password="pass123")
        self.campus = Campus.objects.create(name="Main Campus", code="MAIN")
        self.building = Building.objects.create(
            campus=self.campus,
            name="Main Building",
            code="MB",
        )
        self.room = Room.objects.create(
            building=self.building,
            name="Auditorium",
            code="A1",
            capacity=120,
        )

    def test_authenticated_user_can_list_active_rooms(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/locations/rooms/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"][0]["id"], str(self.room.id))
        self.assertEqual(response.data["data"][0]["name"], "Auditorium")
        self.assertEqual(response.data["data"][0]["code"], "A1")
        self.assertEqual(response.data["data"][0]["capacity"], 120)
        self.assertNotIn("building_name", response.data["data"][0])
        self.assertNotIn("campus_name", response.data["data"][0])

    def test_room_list_supports_search(self):
        Room.objects.create(building=self.building, name="Lab 01", code="LAB01")
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/v1/locations/rooms/?search=lab")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["code"], "LAB01")
