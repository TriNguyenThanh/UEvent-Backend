from rest_framework import serializers

from apps.events.models import Event, EventCategory, EventOrganizer, RegistrationFormField
from apps.locations.models import Room
from apps.users.models import User


class OrganizerEventCategorySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = EventCategory
        fields = ["id", "name", "slug", "color", "icon"]


class OrganizerEventRoomSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField(allow_null=True)
    name = serializers.CharField(allow_blank=True)
    code = serializers.CharField(allow_blank=True)
    building_name = serializers.CharField(allow_blank=True)
    campus_name = serializers.CharField(allow_blank=True)


class OrganizerEventUserSummarySerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "full_name"]

    def get_full_name(self, obj):
        return obj.full_name or obj.get_full_name()


class OrganizerEventOrganizerSummarySerializer(serializers.ModelSerializer):
    user = OrganizerEventUserSummarySerializer(read_only=True)

    class Meta:
        model = EventOrganizer
        fields = ["id", "user", "organizer_role", "joined_at"]


class OrganizerRegistrationFormFieldOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistrationFormField
        fields = [
            "id",
            "field_key",
            "label",
            "field_type",
            "is_required",
            "is_editable_after_submit",
            "options_json",
            "sort_order",
        ]


class OrganizerEventListOutputSerializer(serializers.ModelSerializer):
    category = OrganizerEventCategorySummarySerializer(read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "slug",
            "status",
            "visibility",
            "category",
            "start_at",
            "end_at",
            "max_capacity",
            "cover_image_url",
            "created_at",
            "updated_at",
        ]


class OrganizerEventDetailOutputSerializer(OrganizerEventListOutputSerializer):
    room = serializers.SerializerMethodField()
    created_by = OrganizerEventUserSummarySerializer(read_only=True)
    organizers = OrganizerEventOrganizerSummarySerializer(many=True, read_only=True)
    registration_fields = OrganizerRegistrationFormFieldOutputSerializer(many=True, read_only=True)

    class Meta(OrganizerEventListOutputSerializer.Meta):
        fields = OrganizerEventListOutputSerializer.Meta.fields + [
            "description",
            "room",
            "created_by",
            "organizers",
            "registration_fields",
            "registration_open_at",
            "registration_close_at",
            "cancellation_deadline_at",
            "location_snapshot",
            "deep_link",
        ]

    def get_room(self, obj):
        room = obj.room
        if room is None:
            return None

        building = getattr(room, "building", None)
        campus = getattr(building, "campus", None) if building is not None else None
        return {
            "id": room.id,
            "name": room.name,
            "code": room.code,
            "building_name": getattr(building, "name", ""),
            "campus_name": getattr(campus, "name", ""),
        }


class OrganizerEventInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=True)
    category = serializers.UUIDField(required=True)
    room = serializers.UUIDField(required=False, allow_null=True, default=None)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    visibility = serializers.ChoiceField(
        choices=[Event.Visibility.PUBLIC, Event.Visibility.PRIVATE],
        required=False,
        default=Event.Visibility.PUBLIC,
    )
    registration_open_at = serializers.DateTimeField(required=False, allow_null=True, default=None)
    registration_close_at = serializers.DateTimeField(required=False, allow_null=True, default=None)
    cancellation_deadline_at = serializers.DateTimeField(required=False, allow_null=True, default=None)
    start_at = serializers.DateTimeField(required=True)
    end_at = serializers.DateTimeField(required=True)
    max_capacity = serializers.IntegerField(required=False, allow_null=True, default=None)
    location_snapshot = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, default=None
    )
    cover_image_url = serializers.URLField(required=False, allow_blank=True, allow_null=True, default=None)
    deep_link = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, default=None
    )
    status = serializers.ChoiceField(
        choices=[Event.Status.DRAFT, Event.Status.CANCELLED],
        required=False,
        default=Event.Status.DRAFT,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance is not None:
            for field_name, field in self.fields.items():
                field.required = False
                field.default = serializers.empty

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title cannot be blank.")
        return value

    def validate_category(self, value):
        try:
            category = EventCategory.objects.get(pk=value)
        except EventCategory.DoesNotExist:
            raise serializers.ValidationError("Category does not exist.")
        if not category.is_active:
            raise serializers.ValidationError("Category is not active.")
        return value

    def validate_room(self, value):
        if value is None:
            return value
        try:
            Room.objects.get(pk=value)
        except Room.DoesNotExist:
            raise serializers.ValidationError("Room does not exist.")
        return value

    def validate_max_capacity(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Max capacity must be a positive number.")
        return value

    # ---- cross-field validations ----

    def validate(self, data):
        # start_at < end_at when both present
        start_at = data.get("start_at")
        end_at = data.get("end_at")
        if start_at is not None and end_at is not None and start_at >= end_at:
            raise serializers.ValidationError({"end_at": "End time must be after start time."})

        # registration_open_at <= registration_close_at when both present
        reg_open = data.get("registration_open_at")
        reg_close = data.get("registration_close_at")
        if reg_open is not None and reg_close is not None and reg_open > reg_close:
            raise serializers.ValidationError(
                {"registration_close_at": "Registration close must be after registration open."}
            )

        # registration_close_at <= start_at when both present
        if reg_close is not None and start_at is not None and reg_close > start_at:
            raise serializers.ValidationError(
                {"registration_close_at": "Registration must close before event starts."}
            )

        # cancellation_deadline_at <= start_at when both present
        cancel_deadline = data.get("cancellation_deadline_at")
        if cancel_deadline is not None and start_at is not None and cancel_deadline > start_at:
            raise serializers.ValidationError(
                {"cancellation_deadline_at": "Cancellation deadline must be before event starts."}
            )

        return data

    # ---- service data helper ----

    def to_service_data(self):
        return dict(self.validated_data)
