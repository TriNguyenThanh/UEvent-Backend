from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema

from common.responses import success_response
from apps.users.serializers import UserProfileOutputSerializer, UpdateProfileInputSerializer
from apps.users.services import UserService


class UserProfileView(APIView):
    """
    GET  /api/v1/auth/profile — lấy thông tin user hiện tại.
    PATCH /api/v1/auth/profile — cập nhật profile.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get My Profile",
        operation_description="Trả về thông tin profile của user đang đăng nhập.",
        responses={200: UserProfileOutputSerializer()},
        tags=["Mobile Auth"],
    )
    def get(self, request):
        serializer = UserProfileOutputSerializer(request.user)
        return success_response(data=serializer.data, message="Lấy profile thành công.")

    @swagger_auto_schema(
        operation_summary="Update My Profile",
        operation_description="Cập nhật thông tin profile của user đang đăng nhập.",
        request_body=UpdateProfileInputSerializer,
        responses={200: UserProfileOutputSerializer()},
        tags=["Mobile Auth"],
    )
    def patch(self, request):
        input_serializer = UpdateProfileInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        user = UserService.update_profile(request.user, input_serializer.validated_data)
        output = UserProfileOutputSerializer(user)
        return success_response(data=output.data, message="Cập nhật profile thành công.")
