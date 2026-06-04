from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.responses import success_response

from .serializers import (
    DeviceRegistrationInputSerializer,
    DeviceUnregistrationInputSerializer,
    NotificationInboxOutputSerializer,
    NotificationPreferenceInputSerializer,
    NotificationPreferenceOutputSerializer,
    OrganizerNotificationInputSerializer,
    OrganizerNotificationOutputSerializer,
)
from .services.event_notification_service import EventNotificationService
from .services.inbox_service import NotificationInboxService
from .services.preference_service import NotificationPreferenceService


class NotificationInboxView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        recipients = NotificationInboxService.list_for_user(user=request.user)
        data = [
            NotificationInboxService.to_output(recipient) for recipient in recipients
        ]
        return success_response(
            data=NotificationInboxOutputSerializer(data, many=True).data,
            message="Lấy danh sách thông báo thành công.",
        )


class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return success_response(
            data={
                "unread_count": NotificationInboxService.unread_count(user=request.user)
            },
            message="Lấy số thông báo chưa đọc thành công.",
        )


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        recipient = NotificationInboxService.mark_read(
            user=request.user, recipient_id=pk
        )
        return success_response(
            data=NotificationInboxOutputSerializer(
                NotificationInboxService.to_output(recipient)
            ).data,
            message="Đã đánh dấu thông báo là đã đọc.",
        )


class NotificationMarkOpenedView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        recipient = NotificationInboxService.mark_opened(
            user=request.user, recipient_id=pk
        )
        return success_response(
            data=NotificationInboxOutputSerializer(
                NotificationInboxService.to_output(recipient)
            ).data,
            message="Đã ghi nhận mở thông báo.",
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


class NotificationPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        preference = NotificationPreferenceService.get_for_user(user=request.user)
        return success_response(
            data=NotificationPreferenceOutputSerializer(preference).data,
            message="Lấy cài đặt thông báo thành công.",
        )

    def patch(self, request):
        serializer = NotificationPreferenceInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        preference = NotificationPreferenceService.update_for_user(
            user=request.user,
            data=serializer.validated_data,
        )
        return success_response(
            data=NotificationPreferenceOutputSerializer(preference).data,
            message="Đã cập nhật cài đặt thông báo.",
        )


class OrganizerEventNotificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, event_id):
        serializer = OrganizerNotificationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = EventNotificationService.send_organizer_broadcast(
            actor=request.user,
            event_id=event_id,
            title=serializer.validated_data["title"],
            message=serializer.validated_data["message"],
            audience=serializer.validated_data["audience"],
            send_push=serializer.validated_data["send_push"],
        )
        data = {
            "notification_id": result.notification.id,
            "recipient_count": result.recipient_count,
            "queued_count": result.queued_count,
        }
        return success_response(
            data=OrganizerNotificationOutputSerializer(data).data,
            message="Đã xếp hàng gửi thông báo.",
        )
