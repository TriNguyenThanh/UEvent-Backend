import hashlib
from pathlib import PurePath

from django.conf import settings
from django.core.cache import cache
from rest_framework import serializers

from apps.events.models import Event, EventCategory, EventOrganizer, RegistrationFormField
from apps.locations.models import Room
from apps.utils.s3 import S3Client
from apps.users.models import User


ALLOWED_EVENT_UPLOAD_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


class OrganizerEventCategorySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = EventCategory
        fields = ["id", "name", "slug", "color", "icon"]


class PublicEventCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = EventCategory
        fields = ["id", "name", "slug", "description", "color", "icon"]


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


class EventCoverImageUrlMixin(serializers.Serializer):
    cover_image_url = serializers.SerializerMethodField()

    def get_cover_image_url(self, obj):
        object_key = getattr(obj, "cover_image_key", None)
        if not object_key:
            return None

        cache_key = self._cover_image_cache_key(object_key)
        cached_url = cache.get(cache_key)
        if cached_url:
            return cached_url

        s3_client = getattr(self, "_cover_image_s3_client", None)
        if s3_client is None:
            s3_client = S3Client()
            self._cover_image_s3_client = s3_client

        expires_in = settings.AWS_S3_PRESIGNED_URL_EXPIRES
        presigned_url = s3_client.generate_presigned_url(
            object_key,
            method="get_object",
            expires_in=expires_in,
        )
        cache_timeout = self._cover_image_cache_timeout(expires_in)
        if cache_timeout > 0:
            cache.set(cache_key, presigned_url, timeout=cache_timeout)
        return presigned_url

    @staticmethod
    def _cover_image_cache_key(object_key):
        digest = hashlib.sha256(object_key.encode("utf-8")).hexdigest()
        expires_in = settings.AWS_S3_PRESIGNED_URL_EXPIRES
        return f"events:cover_image_url:v1:{expires_in}:{digest}"

    @staticmethod
    def _cover_image_cache_timeout(expires_in):
        configured_timeout = settings.AWS_S3_PRESIGNED_GET_URL_CACHE_TTL
        safe_timeout = max(0, expires_in - 60)
        return min(configured_timeout, safe_timeout)


class OrganizerEventListOutputSerializer(EventCoverImageUrlMixin, serializers.ModelSerializer):
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


class PublicEventSearchOutputSerializer(OrganizerEventListOutputSerializer):
    class Meta(OrganizerEventListOutputSerializer.Meta):
        fields = OrganizerEventListOutputSerializer.Meta.fields + [
            "description",
            "registration_open_at",
            "registration_close_at",
            "location_snapshot",
            "deep_link",
        ]


class PublicEventDetailOutputSerializer(PublicEventSearchOutputSerializer):
    room = serializers.SerializerMethodField()
    registration_fields = OrganizerRegistrationFormFieldOutputSerializer(many=True, read_only=True)

    class Meta(PublicEventSearchOutputSerializer.Meta):
        fields = PublicEventSearchOutputSerializer.Meta.fields + [
            "room",
            "registration_fields",
            "cancellation_deadline_at",
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


class PublicEventSearchQuerySerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True)
    q = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=[Event.Status.APPROVED, Event.Status.ACTIVE],
        required=False,
    )
    ordering = serializers.ChoiceField(
        choices=[
            "start_at",
            "-start_at",
            "created_at",
            "-created_at",
            "updated_at",
            "-updated_at",
            "title",
            "-title",
        ],
        required=False,
    )

    def get_search_value(self):
        return self.validated_data.get("search") or self.validated_data.get("q")

    def get_category_value(self):
        return (self.validated_data.get("category") or "").strip()


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
            "cover_image_key",
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
    cover_image_key = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )
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

    def validate_cover_image_key(self, value):
        if value in (None, ""):
            return value
        clean_value = value.strip().lstrip("/")
        if clean_value.startswith(("http://", "https://")):
            raise serializers.ValidationError("Cover image must be an S3 object key, not a URL.")
        if not clean_value.startswith("events/"):
            raise serializers.ValidationError("Cover image key must be under the events/ prefix.")
        return clean_value

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


class OrganizerEventPresignedUrlInputSerializer(serializers.Serializer):
    file_name = serializers.CharField(max_length=255)
    content_type = serializers.ChoiceField(
        choices=sorted(ALLOWED_EVENT_UPLOAD_CONTENT_TYPES),
        default="image/jpeg",
        required=False,
    )

    def validate_file_name(self, value):
        file_name = PurePath(value).name.strip()
        if not file_name:
            raise serializers.ValidationError("File name cannot be blank.")
        if "." not in file_name:
            raise serializers.ValidationError("File name must include an extension.")
        return file_name


class OrganizerEventPresignedUrlOutputSerializer(serializers.Serializer):
    object_key = serializers.CharField()
    presigned_upload_url = serializers.URLField()
    presigned_url = serializers.URLField()
    method = serializers.CharField()
    expires_in = serializers.IntegerField()
