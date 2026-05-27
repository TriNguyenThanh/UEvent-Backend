from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema

from apps.events.models import Event, EventOrganizer
from apps.events.services import assert_event_organizer, is_event_organizer
from apps.registrations.models import CheckinLog, EventRegistration, Ticket
from apps.registrations.serializers import (
    EventCheckinLogSerializer,
    EventCheckinScanInputSerializer,
    EventCheckinScanResultSerializer,
    EventRoleSerializer,
    RegistrationCancelSerializer,
    RegistrationCreateSerializer,
    RegistrationEventSerializer,
    RegistrationListSerializer,
    RegistrationQrSerializer,
    TicketDetailSerializer,
    TicketUpdateSerializer,
)
from apps.registrations.services import (
    cancel_event_registration,
    create_ticket_for_registration,
    create_event_registration,
    grant_cohost_role_to_registration,
    issue_registration_qr,
    process_checkin_scan,
)
from common.serializers import ApiErrorResponseSerializer


REGISTRATION_ERROR_RESPONSES = {
    400: ApiErrorResponseSerializer(),
    401: ApiErrorResponseSerializer(),
    403: ApiErrorResponseSerializer(),
    404: ApiErrorResponseSerializer(),
    409: ApiErrorResponseSerializer(),
}


def assert_event_owner(actor, event):
    if event.created_by_id == actor.id:
        return
    if EventOrganizer.objects.filter(
        event=event,
        user=actor,
        organizer_role=EventOrganizer.OrganizerRole.OWNER,
    ).exists():
        return
    raise PermissionDenied("Only event owner can perform this action.")


class MyRegistrationListView(generics.ListAPIView):
    """
    GET /api/v1/registrations/me/

    Lists every registration owned by the current user.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RegistrationListSerializer

    @swagger_auto_schema(
        operation_summary="List My Registrations",
        operation_description="Xem toàn bộ đăng ký của người dùng hiện tại.",
        responses={200: RegistrationListSerializer(many=True), **REGISTRATION_ERROR_RESPONSES},
        tags=["Registrations"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):  # type: ignore[override]
        return (
            EventRegistration.objects.filter(user=self.request.user)
            .select_related("event", "user", "ticket")
            .order_by("-registered_at", "-created_at")
        )


class MyRegisteredEventListView(generics.ListAPIView):
    """
    GET /api/v1/events/registrations/me/

    Lists events registered by the current user.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RegistrationEventSerializer

    @swagger_auto_schema(
        operation_summary="List My Registered Events",
        operation_description="Lấy danh sách sự kiện mà người dùng hiện tại đã đăng ký.",
        responses={200: RegistrationEventSerializer(many=True), **REGISTRATION_ERROR_RESPONSES},
        tags=["Registrations"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):  # type: ignore[override]
        return (
            Event.objects.filter(registrations__user=self.request.user)
            .distinct()
            .order_by("-registrations__registered_at", "-registrations__created_at")
        )


class EventRegistrationListCreateView(generics.ListCreateAPIView):
    """
    GET /api/v1/events/{event_id}/registrations/
    POST /api/v1/events/{event_id}/registrations/

    Organizers can list event registrations. Authenticated users can register
    for the event with an optional answers array.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RegistrationListSerializer

    def get_event(self):
        return get_object_or_404(Event.objects.prefetch_related("organizers"), id=self.kwargs["event_id"])

    def get_queryset(self):  # type: ignore[override]
        event = self.get_event()
        if self.request.method == "GET":
            assert_event_organizer(self.request.user, event)
        return (
            EventRegistration.objects.filter(event=event)
            .select_related("event", "user", "ticket")
            .order_by("-registered_at", "-created_at")
        )

    @swagger_auto_schema(
        operation_summary="List Event Registrations",
        operation_description="Organizer xem danh sách đăng ký của một sự kiện.",
        responses={200: RegistrationListSerializer(many=True), **REGISTRATION_ERROR_RESPONSES},
        tags=["Registrations"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Register For Event",
        operation_description="User đăng ký tham gia sự kiện theo event_id trên URL.",
        request_body=RegistrationCreateSerializer,
        responses={201: RegistrationListSerializer(), **REGISTRATION_ERROR_RESPONSES},
        tags=["Registrations"],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = RegistrationCreateSerializer(
            data=request.data,
            context={"event_id": self.kwargs["event_id"]},
        )
        serializer.is_valid(raise_exception=True)

        registration = create_event_registration(
            user=request.user,
            event_id=self.kwargs["event_id"],
            answers=serializer.validated_data.get("answers", []),
        )
        response_serializer = RegistrationListSerializer(registration)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class EventRegistrationDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/events/{event_id}/registrations/{registration_id}/

    Organizer-only registration detail.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RegistrationListSerializer
    lookup_url_kwarg = "registration_id"

    def get_queryset(self):  # type: ignore[override]
        event = get_object_or_404(Event.objects.prefetch_related("organizers"), id=self.kwargs["event_id"])
        assert_event_organizer(self.request.user, event)
        return EventRegistration.objects.filter(event=event).select_related("event", "user", "ticket")

    @swagger_auto_schema(
        operation_summary="Get Event Registration Detail",
        operation_description="Organizer xem chi tiết một đăng ký trong sự kiện.",
        responses={200: RegistrationListSerializer(), **REGISTRATION_ERROR_RESPONSES},
        tags=["Registrations"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class OrganizerEventRegistrationListView(generics.ListAPIView):
    """
    GET /api/v1/organizer/events/{event_id}/registrations/

    Organizer-only alias for listing event registrations.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RegistrationListSerializer

    def get_queryset(self):  # type: ignore[override]
        event = get_object_or_404(Event.objects.prefetch_related("organizers"), id=self.kwargs["event_id"])
        assert_event_organizer(self.request.user, event)
        return (
            EventRegistration.objects.filter(event=event)
            .select_related("event", "user", "ticket")
            .order_by("-registered_at", "-created_at")
        )

    @swagger_auto_schema(
        operation_summary="List Organizer Event Registrations",
        operation_description="Organizer xem danh sách người đăng ký của một sự kiện.",
        responses={200: RegistrationListSerializer(many=True), **REGISTRATION_ERROR_RESPONSES},
        tags=["Registrations"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class EventAttendeeListView(generics.ListAPIView):
    """
    GET /api/v1/events/{event_id}/attendees/

    Organizer-only attendee list with status and search filters for check-in.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RegistrationListSerializer

    def get_event(self):
        event = get_object_or_404(Event.objects.prefetch_related("organizers"), id=self.kwargs["event_id"])
        assert_event_organizer(self.request.user, event)
        return event

    def get_queryset(self):  # type: ignore[override]
        params = self.request.query_params
        queryset = (
            EventRegistration.objects.filter(event=self.get_event())
            .select_related("event", "user", "ticket")
            .order_by("-registered_at", "-created_at")
        )

        status_filter = params.get("status")
        if status_filter == "checked_in":
            queryset = queryset.filter(status=EventRegistration.RegistrationStatus.CHECKED_IN)
        elif status_filter == "not_checked_in":
            queryset = queryset.filter(
                status__in=[
                    EventRegistration.RegistrationStatus.REGISTERED,
                    EventRegistration.RegistrationStatus.WAITLISTED,
                ]
            )
        elif status_filter:
            queryset = queryset.filter(status=status_filter)

        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(user__username__icontains=search)
                | Q(user__full_name__icontains=search)
                | Q(user__email__icontains=search)
                | Q(ticket__ticket_code__icontains=search)
            )
        return queryset

    @swagger_auto_schema(
        operation_summary="List Event Attendees",
        operation_description="Organizer xem danh sách attendee của sự kiện để phục vụ check-in.",
        responses={200: RegistrationListSerializer(many=True), **REGISTRATION_ERROR_RESPONSES},
        tags=["Check-in"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class EventCheckinScanView(APIView):
    """
    POST /api/v1/events/{event_id}/check-in/scan/

    Organizer scans a ticket code or signed QR payload and records check-in.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Scan Event Check-in",
        operation_description="Organizer quét QR hoặc nhập mã vé để check-in attendee.",
        request_body=EventCheckinScanInputSerializer,
        responses={200: EventCheckinScanResultSerializer(), **REGISTRATION_ERROR_RESPONSES},
        tags=["Check-in"],
    )
    def post(self, request, event_id):
        event = get_object_or_404(Event.objects.prefetch_related("organizers"), id=event_id)
        assert_event_organizer(request.user, event)

        serializer = EventCheckinScanInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scan_data = serializer.validated_data
        result = process_checkin_scan(
            event_id=event.id,
            ticket_code=scan_data.get("ticket_code"),
            email=scan_data.get("email"),
            qr_payload=scan_data.get("qr_payload"),
            qr_signature=scan_data.get("qr_signature"),
            scanner_user=request.user,
            note=scan_data.get("note"),
        )
        return Response(EventCheckinScanResultSerializer(result).data, status=status.HTTP_200_OK)


class EventCheckinLogListView(generics.ListAPIView):
    """
    GET /api/v1/events/{event_id}/check-ins/

    Organizer-only check-in log list for an event.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = EventCheckinLogSerializer

    def get_event(self):
        event = get_object_or_404(Event.objects.prefetch_related("organizers"), id=self.kwargs["event_id"])
        assert_event_organizer(self.request.user, event)
        return event

    def get_queryset(self):  # type: ignore[override]
        params = self.request.query_params
        queryset = (
            CheckinLog.objects.filter(event=self.get_event())
            .select_related(
                "event",
                "scanner_user",
                "ticket",
                "ticket__registration",
                "ticket__registration__event",
                "ticket__registration__user",
            )
            .order_by("-checked_in_at", "-created_at")
        )

        result_filter = params.get("result")
        if result_filter:
            queryset = queryset.filter(result=result_filter)

        ticket_id = params.get("ticket_id")
        if ticket_id:
            queryset = queryset.filter(ticket_id=ticket_id)

        user_id = params.get("user_id")
        if user_id:
            queryset = queryset.filter(ticket__registration__user_id=user_id)

        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(ticket__ticket_code__icontains=search)
                | Q(ticket__registration__user__username__icontains=search)
                | Q(ticket__registration__user__full_name__icontains=search)
                | Q(ticket__registration__user__email__icontains=search)
                | Q(scanner_user__username__icontains=search)
                | Q(scanner_user__email__icontains=search)
            )
        return queryset

    @swagger_auto_schema(
        operation_summary="List Event Check-in Logs",
        operation_description="Organizer xem lịch sử check-in của một sự kiện.",
        responses={200: EventCheckinLogSerializer(many=True), **REGISTRATION_ERROR_RESPONSES},
        tags=["Check-in"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class OrganizerRegistrationGrantCohostView(APIView):
    """
    POST /api/v1/organizer/events/{event_id}/registrations/{registration_id}/cohost/

    Event owner grants co-host role to the selected registration user.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Grant Co-host Role",
        operation_description="Owner cấp quyền co-host cho người dùng đã đăng ký sự kiện.",
        responses={200: EventRoleSerializer(), **REGISTRATION_ERROR_RESPONSES},
        tags=["Registrations"],
    )
    def post(self, request, event_id, registration_id):
        event = get_object_or_404(Event.objects.prefetch_related("organizers"), id=event_id)
        assert_event_owner(request.user, event)
        role = grant_cohost_role_to_registration(event=event, registration_id=registration_id)
        return Response(EventRoleSerializer(role).data, status=status.HTTP_200_OK)


class MyEventRegistrationCancelView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get My Event Registration",
        operation_description="User xem thông tin đăng ký của bản thân trong một sự kiện.",
        responses={200: RegistrationListSerializer(), **REGISTRATION_ERROR_RESPONSES},
        tags=["Registrations"],
    )
    def get(self, request, event_id):
        registration = get_object_or_404(
            EventRegistration.objects.select_related("event", "user", "ticket"),
            event_id=event_id,
            user=request.user,
        )
        return Response(RegistrationListSerializer(registration).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="Cancel My Event Registration",
        operation_description="User hủy đăng ký của bản thân trong một sự kiện.",
        responses={200: RegistrationListSerializer(), **REGISTRATION_ERROR_RESPONSES},
        tags=["Registrations"],
    )
    def delete(self, request, event_id):
        registration = get_object_or_404(
            EventRegistration.objects.select_related("event", "user", "ticket"),
            event_id=event_id,
            user=request.user,
        )
        registration = cancel_event_registration(registration=registration)
        return Response(RegistrationListSerializer(registration).data, status=status.HTTP_200_OK)


class OrganizerRegistrationCancelView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Organizer Cancel Registration",
        operation_description="Organizer hủy đăng ký của người tham gia.",
        request_body=RegistrationCancelSerializer,
        responses={200: RegistrationListSerializer(), **REGISTRATION_ERROR_RESPONSES},
        tags=["Registrations"],
    )
    def patch(self, request, event_id, registration_id):
        event = get_object_or_404(Event.objects.prefetch_related("organizers"), id=event_id)
        assert_event_organizer(request.user, event)
        serializer = RegistrationCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration = get_object_or_404(
            EventRegistration.objects.select_related("event", "user", "ticket"),
            id=registration_id,
            event=event,
        )
        registration = cancel_event_registration(
            registration=registration,
            reason=serializer.validated_data.get("reason"),
        )
        return Response(RegistrationListSerializer(registration).data, status=status.HTTP_200_OK)


class TicketListView(generics.ListAPIView):
    """
    GET /api/v1/tickets/me/

    Lists tickets for the current user.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TicketDetailSerializer

    @swagger_auto_schema(
        operation_summary="List My Tickets",
        operation_description="Xem danh sách vé của người dùng hiện tại.",
        responses={200: TicketDetailSerializer(many=True), **REGISTRATION_ERROR_RESPONSES},
        tags=["Tickets"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):  # type: ignore[override]
        return (
            Ticket.objects.filter(registration__user=self.request.user)
            .select_related("registration", "registration__event")
            .order_by("-issued_at", "-created_at")
        )


def get_user_ticket_for_event(*, event_id, user):
    return get_object_or_404(
        Ticket.objects.select_related("registration", "registration__event", "registration__user"),
        registration__event_id=event_id,
        registration__user_id=user.id,
    )


class EventTicketDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get My Event Ticket Detail",
        operation_description="User xem chi tiết vé của bản thân trong một sự kiện theo event id.",
        responses={200: TicketDetailSerializer(), **REGISTRATION_ERROR_RESPONSES},
        tags=["Tickets"],
    )
    def get(self, request, event_id):
        ticket = get_user_ticket_for_event(event_id=event_id, user=request.user)
        return Response(TicketDetailSerializer(ticket).data, status=status.HTTP_200_OK)


class EventTicketQrAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get My Event Ticket QR",
        operation_description="User lấy QR payload tạm thời của vé trong một sự kiện theo event id.",
        responses={200: RegistrationQrSerializer(), **REGISTRATION_ERROR_RESPONSES},
        tags=["Tickets"],
    )
    def get(self, request, event_id):
        ticket = get_user_ticket_for_event(event_id=event_id, user=request.user)
        qr_data = issue_registration_qr(registration=ticket.registration)
        serializer = RegistrationQrSerializer(qr_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TicketDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TicketDetailSerializer
    lookup_field = "registration_id"
    lookup_url_kwarg = "registration_id"

    def get_queryset(self):  # type: ignore[override]
        return Ticket.objects.select_related("registration", "registration__event", "registration__user")

    def get_object(self):
        ticket = super().get_object()
        if ticket.registration.user_id != self.request.user.id and not is_event_organizer(
            self.request.user,
            ticket.registration.event,
        ):
            raise PermissionDenied("You do not have access to this ticket.")
        return ticket

    @swagger_auto_schema(
        operation_summary="Get Ticket Detail",
        operation_description="User hoặc organizer xem chi tiết vé theo registration id.",
        responses={200: TicketDetailSerializer(), **REGISTRATION_ERROR_RESPONSES},
        tags=["Tickets"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Ticket",
        operation_description="Organizer tạo vé cho một registration đã được đăng ký.",
        responses={201: TicketDetailSerializer(), **REGISTRATION_ERROR_RESPONSES},
        tags=["Tickets"],
    )
    def post(self, request, registration_id):
        registration = get_object_or_404(
            EventRegistration.objects.select_related("event", "user"),
            id=registration_id,
        )
        assert_event_organizer(request.user, registration.event)
        ticket = create_ticket_for_registration(registration=registration)
        return Response(TicketDetailSerializer(ticket).data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Update Ticket",
        operation_description="Organizer cập nhật trạng thái hoặc hạn sử dụng của vé theo registration id.",
        request_body=TicketUpdateSerializer,
        responses={200: TicketDetailSerializer(), **REGISTRATION_ERROR_RESPONSES},
        tags=["Tickets"],
    )
    def patch(self, request, *args, **kwargs):
        ticket = self.get_object()
        if not is_event_organizer(request.user, ticket.registration.event):
            raise PermissionDenied("Only event organizers can update this ticket.")

        serializer = TicketUpdateSerializer(ticket, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TicketDetailSerializer(ticket).data, status=status.HTTP_200_OK)


class TicketQrAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get Ticket QR",
        operation_description="Lấy QR payload tạm thời từ registration id.",
        responses={200: RegistrationQrSerializer(), **REGISTRATION_ERROR_RESPONSES},
        tags=["Tickets"],
    )
    def get(self, request, registration_id):
        ticket = get_object_or_404(
            Ticket.objects.select_related("registration", "registration__event", "registration__user"),
            registration_id=registration_id,
        )
        if ticket.registration.user_id != request.user.id and not is_event_organizer(
            request.user,
            ticket.registration.event,
        ):
            raise PermissionDenied("You do not have access to this ticket.")

        qr_data = issue_registration_qr(registration=ticket.registration)
        serializer = RegistrationQrSerializer(qr_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TicketCancelView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Cancel Ticket",
        operation_description="User hoặc organizer hủy vé và registration liên quan.",
        request_body=RegistrationCancelSerializer,
        responses={200: RegistrationListSerializer(), **REGISTRATION_ERROR_RESPONSES},
        tags=["Tickets"],
    )
    def patch(self, request, registration_id):
        ticket = get_object_or_404(
            Ticket.objects.select_related("registration", "registration__event", "registration__user"),
            registration_id=registration_id,
        )
        if ticket.registration.user_id != request.user.id and not is_event_organizer(
            request.user,
            ticket.registration.event,
        ):
            raise PermissionDenied("You do not have access to this ticket.")
        serializer = RegistrationCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration = cancel_event_registration(
            registration=ticket.registration,
            reason=serializer.validated_data.get("reason"),
        )
        return Response(RegistrationListSerializer(registration).data, status=status.HTTP_200_OK)
