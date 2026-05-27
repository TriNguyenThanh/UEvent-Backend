from rest_framework import serializers

from apps.events.models import Event, EventCategory


class AdminCategoryOutputSerializer(serializers.ModelSerializer):
    event_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = EventCategory
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "icon",
            "color",
            "is_active",
            "event_count",
            "created_at",
            "updated_at",
        ]


class AdminCategoryInputSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(required=False, allow_blank=True, max_length=140)

    class Meta:
        model = EventCategory
        fields = ["name", "slug", "description", "icon", "color", "is_active"]

    def validate_name(self, value):
        query = EventCategory.all_objects.filter(name=value)
        if self.instance is not None:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError("Tên danh mục đã tồn tại.")
        return value

    def validate_slug(self, value):
        if not value:
            return value

        query = EventCategory.all_objects.filter(slug=value)
        if self.instance is not None:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise serializers.ValidationError("Slug danh mục đã tồn tại.")
        return value

    def to_service_data(self):
        return dict(self.validated_data)


class PopularCategorySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    event_count = serializers.IntegerField()


class AdminCategoryStatisticsOutputSerializer(serializers.Serializer):
    total_categories = serializers.IntegerField()
    active_categories = serializers.IntegerField()
    total_events = serializers.IntegerField()
    popular_category = PopularCategorySerializer(allow_null=True)
