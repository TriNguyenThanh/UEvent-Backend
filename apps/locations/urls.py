from django.urls import path

from .views import RoomListView


app_name = "locations"

urlpatterns = [
    path("locations/rooms/", RoomListView.as_view(), name="room-list"),
]
