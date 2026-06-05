import uuid

from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.users.serializers import (
    UserAvatarPresignedUrlInputSerializer,
    UserAvatarPresignedUrlOutputSerializer,
)
from apps.utils.s3 import S3Client
from common.responses import success_response


class UserAvatarPresignedUrlView(APIView):
    """POST /api/v1/auth/profile/avatar/presigned-url/ - tạo URL upload avatar."""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create Profile Avatar Upload URL",
        operation_description="Tạo presigned S3 URL để mobile upload avatar người dùng.",
        request_body=UserAvatarPresignedUrlInputSerializer,
        responses={200: UserAvatarPresignedUrlOutputSerializer()},
        tags=["Mobile Auth"],
    )
    def post(self, request):
        input_serializer = UserAvatarPresignedUrlInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        file_name = input_serializer.validated_data["file_name"]
        content_type = input_serializer.validated_data["content_type"]
        object_key = f"users/{request.user.id}/avatars/{uuid.uuid4().hex}-{file_name}"

        s3_client = S3Client()
        expires_in = settings.AWS_S3_PRESIGNED_URL_EXPIRES
        presigned_url = s3_client.generate_presigned_url(
            object_key,
            method="put_object",
            expires_in=expires_in,
            params={"ContentType": content_type},
        )

        output_serializer = UserAvatarPresignedUrlOutputSerializer(
            {
                "object_key": object_key,
                "presigned_upload_url": presigned_url,
                "presigned_url": presigned_url,
                "method": "PUT",
                "expires_in": expires_in,
            }
        )
        return success_response(
            data=output_serializer.data,
            message="Tạo URL upload avatar thành công.",
        )
