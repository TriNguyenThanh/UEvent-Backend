from rest_framework import serializers

from apps.locations.models import Building, Campus, Room


class AdminCampusSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Campus
        fields = ["id", "name", "code"]


class AdminBuildingSummarySerializer(serializers.ModelSerializer):
    campus = AdminCampusSummarySerializer(read_only=True)

    class Meta:
        model = Building
        fields = ["id", "name", "code", "campus"]


class AdminCampusOutputSerializer(serializers.ModelSerializer):
    building_count = serializers.IntegerField(read_only=True)
    room_count = serializers.IntegerField(read_only=True)
    event_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Campus
        fields = [
            "id",
            "name",
            "code",
            "address",
            "is_active",
            "building_count",
            "room_count",
            "event_count",
            "created_at",
            "updated_at",
        ]


class AdminBuildingOutputSerializer(serializers.ModelSerializer):
    campus = AdminCampusSummarySerializer(read_only=True)
    room_count = serializers.IntegerField(read_only=True)
    event_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Building
        fields = [
            "id",
            "campus",
            "name",
            "code",
            "is_active",
            "room_count",
            "event_count",
            "created_at",
            "updated_at",
        ]


class AdminRoomOutputSerializer(serializers.ModelSerializer):
    building = AdminBuildingSummarySerializer(read_only=True)
    event_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Room
        fields = [
            "id",
            "building",
            "name",
            "code",
            "capacity",
            "is_active",
            "event_count",
            "created_at",
            "updated_at",
        ]


class AdminCampusInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campus
        fields = ["name", "code", "address", "is_active"]
        extra_kwargs = {
            "name": {"required": True, "allow_blank": False},
            "code": {"required": True, "allow_blank": False},
            "address": {"required": False, "allow_blank": True},
            "is_active": {"required": False},
        }

    def validate_name(self, value):
        name = value.strip()
        query = Campus.all_objects.filter(name__iexact=name)
        if self.instance is not None:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError("Tên cơ sở đã tồn tại.")
        return name

    def validate_code(self, value):
        code = value.strip()
        if not code:
            raise serializers.ValidationError("Mã cơ sở không được để trống.")

        query = Campus.all_objects.filter(code__iexact=code)
        if self.instance is not None:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError("Mã cơ sở đã tồn tại.")
        return code.upper()

    def to_service_data(self):
        return dict(self.validated_data)


class AdminBuildingInputSerializer(serializers.ModelSerializer):
    campus_id = serializers.PrimaryKeyRelatedField(
        queryset=Campus.objects.all(),
        source="campus",
        required=True,
    )

    class Meta:
        model = Building
        fields = ["campus_id", "name", "code", "is_active"]
        validators = []
        extra_kwargs = {
            "name": {"required": True, "allow_blank": False},
            "code": {"required": True, "allow_blank": False},
            "is_active": {"required": False},
        }

    def validate_name(self, value):
        return value.strip()

    def validate_code(self, value):
        code = value.strip()
        if not code:
            raise serializers.ValidationError("Mã tòa nhà không được để trống.")
        return code.upper()

    def validate(self, attrs):
        campus = attrs.get("campus") or getattr(self.instance, "campus", None)
        code = attrs.get("code") or getattr(self.instance, "code", "")
        if campus and code:
            query = Building.all_objects.filter(campus=campus, code__iexact=code)
            if self.instance is not None:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                raise serializers.ValidationError({"code": "Mã tòa nhà đã tồn tại trong cơ sở này."})
        return attrs

    def to_service_data(self):
        return dict(self.validated_data)


class AdminRoomInputSerializer(serializers.ModelSerializer):
    building_id = serializers.PrimaryKeyRelatedField(
        queryset=Building.objects.select_related("campus"),
        source="building",
        required=True,
    )

    class Meta:
        model = Room
        fields = ["building_id", "name", "code", "capacity", "is_active"]
        validators = []
        extra_kwargs = {
            "name": {"required": True, "allow_blank": False},
            "code": {"required": True, "allow_blank": False},
            "capacity": {"required": False, "allow_null": True},
            "is_active": {"required": False},
        }

    def validate_name(self, value):
        return value.strip()

    def validate_code(self, value):
        code = value.strip()
        if not code:
            raise serializers.ValidationError("Mã phòng không được để trống.")
        return code.upper()

    def validate_capacity(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Sức chứa phải lớn hơn 0.")
        return value

    def validate(self, attrs):
        building = attrs.get("building") or getattr(self.instance, "building", None)
        code = attrs.get("code") or getattr(self.instance, "code", "")
        if building and code:
            query = Room.all_objects.filter(building=building, code__iexact=code)
            if self.instance is not None:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                raise serializers.ValidationError({"code": "Mã phòng đã tồn tại trong tòa nhà này."})
        return attrs

    def to_service_data(self):
        return dict(self.validated_data)


class AdminLocationStatisticsOutputSerializer(serializers.Serializer):
    total_campuses = serializers.IntegerField()
    active_campuses = serializers.IntegerField()
    total_buildings = serializers.IntegerField()
    active_buildings = serializers.IntegerField()
    total_rooms = serializers.IntegerField()
    active_rooms = serializers.IntegerField()
    rooms_with_events = serializers.IntegerField()
    total_capacity = serializers.IntegerField()
