from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema

from apps.events.models import Event
from apps.registrations.models import EventRegistration, Ticket
from apps.registrations.permissions import IsRegistrationOwner
from apps.registrations.serializers import (
    RegistrationCancelSerializer,
    RegistrationCreateSerializer,
    RegistrationListSerializer,
    RegistrationQrSerializer,
    TicketDetailSerializer,
)
from apps.registrations.services import (
    cancel_event_registration,
    create_event_registration,
    issue_registration_qr,
)
from common.serializers import ApiErrorResponseSerializer


REGISTRATION_ERROR_RESPONSES = {
    400: ApiErrorResponseSerializer(),
    401: ApiErrorResponseSerializer(),
    403: ApiErrorResponseSerializer(),
    404: ApiErrorResponseSerializer(),
    409: ApiErrorResponseSerializer(),
}


def is_event_organizer(user, event):
    if not user or not user.is_authenticated:
        return False
    if event.created_by_id == user.id:
        return True
    return event.organizers.filter(user=user).exists()


def assert_event_organizer(request, event):
    if not is_event_organizer(request.user, event):
        raise PermissionDenied("You do not have organizer access to this event.")


class RegistrationListCreateView(generics.ListCreateAPIView):
    """
    Backward-compatible registration endpoint.

    GET /api/v1/registrations/
    POST /api/v1/registrations/ {"event_id": "...", "answers": []}
    """
    permission_classes = [IsAuthenticated]
    serializer_class = RegistrationListSerializer

    def get_queryset(self): # type: ignore
        return (
            EventRegistration.objects.filter(user=self.request.user)
            .select_related("event", "user", "ticket")
            .order_by("-registered_at", "-created_at")
        )

    @swagger_auto_schema(
        operation_summary="List Registrations",
        operation_description="Lấy danh sách đăng ký sự kiện của người dùng hiện tại (có phân trang).",
        responses={
            200: RegistrationListSerializer(many=True),
            **REGISTRATION_ERROR_RESPONSES,
        },
        tags=["Registrations"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create Registration",
        operation_description="Đăng ký tham gia sự kiện theo event_id.",
        request_body=RegistrationCreateSerializer,
        responses={
            201: RegistrationListSerializer(),
            **REGISTRATION_ERROR_RESPONSES,
        },
        tags=["Registrations"],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        serializer = RegistrationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        registration = create_event_registration(
            user=request.user,
            **serializer.validated_data,
        )
        response_serializer = RegistrationListSerializer(registration)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


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
            assert_event_organizer(self.request, event)
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
        assert_event_organizer(self.request, event)
        return EventRegistration.objects.filter(event=event).select_related("event", "user", "ticket")

    @swagger_auto_schema(
        operation_summary="Get Event Registration Detail",
        operation_description="Organizer xem chi tiết một đăng ký trong sự kiện.",
        responses={200: RegistrationListSerializer(), **REGISTRATION_ERROR_RESPONSES},
        tags=["Registrations"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class MyEventRegistrationCancelView(APIView):
    permission_classes = [IsAuthenticated]

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
        assert_event_organizer(request, event)
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


class RegistrationQrAPIView(APIView):
    permission_classes = [IsAuthenticated, IsRegistrationOwner]

    @swagger_auto_schema(
        operation_summary="Get Registration QR",
        operation_description="Lấy QR payload tạm thời để check-in cho registration (chỉ owner được phép).",
        responses={
            200: RegistrationQrSerializer(),
            **REGISTRATION_ERROR_RESPONSES,
        },
        tags=["Registrations"],
    )
    def get(self, request, id):
        registration = get_object_or_404(
            EventRegistration.objects.select_related("event", "ticket"),
            id=id,
        )
        self.check_object_permissions(request, registration)

        qr_data = issue_registration_qr(registration=registration)
        serializer = RegistrationQrSerializer(qr_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


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


class TicketDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TicketDetailSerializer
    lookup_url_kwarg = "ticket_id"

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
        operation_description="User hoặc organizer xem chi tiết vé.",
        responses={200: TicketDetailSerializer(), **REGISTRATION_ERROR_RESPONSES},
        tags=["Tickets"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class TicketQrAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get Ticket QR",
        operation_description="Lấy QR payload tạm thời từ ticket id.",
        responses={200: RegistrationQrSerializer(), **REGISTRATION_ERROR_RESPONSES},
        tags=["Tickets"],
    )
    def get(self, request, ticket_id):
        ticket = get_object_or_404(
            Ticket.objects.select_related("registration", "registration__event", "registration__user"),
            id=ticket_id,
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
    def patch(self, request, ticket_id):
        ticket = get_object_or_404(
            Ticket.objects.select_related("registration", "registration__event", "registration__user"),
            id=ticket_id,
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
