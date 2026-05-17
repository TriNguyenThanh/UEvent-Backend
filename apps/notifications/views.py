from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.responses import success_response

from .serializers import (
    DeviceRegistrationInputSerializer,
    DeviceUnregistrationInputSerializer,
    NotificationInboxOutputSerializer,
)
from .services.inbox_service import NotificationInboxService


class NotificationInboxView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        recipients = NotificationInboxService.list_for_user(user=request.user)
        data = [
            NotificationInboxService.to_output(recipient)
            for recipient in recipients
        ]
        return success_response(
            data=NotificationInboxOutputSerializer(data, many=True).data,
            message="Lấy danh sách thông báo thành công.",
        )


class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return success_response(
            data={"unread_count": NotificationInboxService.unread_count(user=request.user)},
            message="Lấy số thông báo chưa đọc thành công.",
        )


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        recipient = NotificationInboxService.mark_read(user=request.user, recipient_id=pk)
        return success_response(
            data=NotificationInboxOutputSerializer(NotificationInboxService.to_output(recipient)).data,
            message="Đã đánh dấu thông báo là đã đọc.",
        )


class NotificationRegisterDeviceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DeviceRegistrationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = NotificationInboxService.register_device(
            user=request.user,
            fcm_token=serializer.validated_data["fcm_token"],
            device_name=serializer.validated_data.get("device_name", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return success_response(
            data={"device_session_id": result["id"], "created": result["created"]},
            message="Đã đăng ký thiết bị nhận thông báo.",
        )


class NotificationUnregisterDeviceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DeviceUnregistrationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_count = NotificationInboxService.unregister_device(
            user=request.user,
            fcm_token=serializer.validated_data["fcm_token"],
        )
        return success_response(
            data={"updated_count": updated_count},
            message="Đã hủy đăng ký thiết bị nhận thông báo.",
        )
