from pathlib import PurePath

from django.core.exceptions import ImproperlyConfigured
from rest_framework import serializers

from apps.organizer_requests.models import OrganizerRequest
from apps.utils.s3 import S3Client


ALLOWED_ORGANIZER_REQUEST_PROOF_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}


class OrganizerRequestProofUploadInputSerializer(serializers.Serializer):
    file_name = serializers.CharField(max_length=255)
    content_type = serializers.ChoiceField(
        choices=sorted(ALLOWED_ORGANIZER_REQUEST_PROOF_CONTENT_TYPES),
    )

    def validate_file_name(self, value):
        file_name = PurePath(value).name.strip()
        if not file_name:
            raise serializers.ValidationError("Tên file không được để trống.")
        if "." not in file_name:
            raise serializers.ValidationError("Tên file phải có phần mở rộng.")
        return file_name


class OrganizerRequestProofUploadOutputSerializer(serializers.Serializer):
    object_key = serializers.CharField()
    presigned_upload_url = serializers.URLField()
    presigned_url = serializers.URLField()
    method = serializers.CharField()
    expires_in = serializers.IntegerField()


class OrganizerRequestCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000, trim_whitespace=True)
    proof_file_key = serializers.CharField(max_length=500)
    proof_file_name = serializers.CharField(max_length=255)

    def validate_reason(self, value):
        if len(value.strip()) < 20:
            raise serializers.ValidationError("Lý do cần có ít nhất 20 ký tự.")
        return value.strip()

    def validate_proof_file_key(self, value):
        clean_value = value.strip().lstrip("/")
        if not clean_value:
            raise serializers.ValidationError("Tài liệu chứng minh là bắt buộc.")
        if not clean_value.startswith("organizer-requests/"):
            raise serializers.ValidationError(
                "File chứng minh phải nằm trong thư mục organizer-requests/."
            )
        return clean_value

    def validate_proof_file_name(self, value):
        file_name = PurePath(value).name.strip()
        if not file_name:
            raise serializers.ValidationError("Tên file chứng minh không được để trống.")
        return file_name


class OrganizerRequestOutputSerializer(serializers.ModelSerializer):
    proof_file_url = serializers.SerializerMethodField()
    reviewed_by = serializers.SerializerMethodField()

    class Meta:
        model = OrganizerRequest
        fields = [
            "id",
            "status",
            "reason",
            "proof_file_key",
            "proof_file_name",
            "proof_file_url",
            "reviewed_by",
            "reviewed_at",
            "review_note",
            "created_at",
            "updated_at",
        ]

    def get_proof_file_url(self, obj):
        if not obj.proof_file_key:
            return ""
        try:
            return S3Client().generate_presigned_url(obj.proof_file_key)
        except (ImproperlyConfigured, ValueError):
            return ""

    def get_reviewed_by(self, obj):
        if obj.reviewed_by is None:
            return None
        return {
            "id": obj.reviewed_by_id,
            "username": obj.reviewed_by.username,
            "full_name": obj.reviewed_by.full_name,
            "email": obj.reviewed_by.email,
        }


class AdminOrganizerRequestUserSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField()
    email = serializers.EmailField()
    full_name = serializers.CharField(allow_blank=True)
    student_code = serializers.CharField(allow_blank=True, allow_null=True)
    faculty = serializers.CharField(allow_blank=True, allow_null=True)


class AdminOrganizerRequestOutputSerializer(OrganizerRequestOutputSerializer):
    user = AdminOrganizerRequestUserSerializer(read_only=True)

    class Meta(OrganizerRequestOutputSerializer.Meta):
        fields = OrganizerRequestOutputSerializer.Meta.fields + ["user"]


class AdminOrganizerRequestReviewSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=1000, required=False, allow_blank=True)
