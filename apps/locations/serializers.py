from rest_framework import serializers

from apps.locations.models import Room


class RoomListOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = [
            "id",
            "name",
            "code",
            "capacity",
        ]
