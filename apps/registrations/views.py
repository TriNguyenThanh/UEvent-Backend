from typing import cast

from django.shortcuts import get_object_or_404
from rest_framework import filters, status, viewsets
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from apps.events.models import Event, EventOrganizer
from apps.registrations.models import Ticket
from apps.registrations.permissions import (
	CHECKIN_ROLES,
	IsEventCheckinStaff,
	IsEventHost,
	IsEventHostForEvent,
	IsTicketOwnerOrOrganizer,
	user_has_event_role,
)
from apps.registrations.serializers import (
	CheckinScanSerializer,
	EventCohostCreateSerializer,
	EventCohostUpdateSerializer,
	EventOrganizerSerializer,
	TicketCreateSerializer,
	TicketDetailSerializer,
	TicketListSerializer,
	TicketUpdateSerializer,
)
from apps.registrations.services import process_checkin_scan
from apps.users.models import User


class TicketViewSet(viewsets.ModelViewSet):
	"""Manage tickets with role-based access for users and organizers."""

	serializer_class = TicketDetailSerializer
	permission_classes = [IsAuthenticated]
	http_method_names = ["get", "post", "patch", "delete", "head", "options"]
	filter_backends = [filters.SearchFilter, filters.OrderingFilter]
	search_fields = [
		"ticket_code",
		"registration__user__username",
		"registration__user__full_name",
		"registration__event__title",
	]
	ordering_fields = ["issued_at", "expires_at", "created_at", "status"]
	ordering = ["-issued_at"]

	def get_queryset(self):  # type: ignore[override]
		queryset = Ticket.objects.select_related(
			"registration",
			"registration__event",
			"registration__user",
		)
		request = cast(Request, self.request)
		user = request.user
		event_id = request.query_params.get("event_id")
		status_value = request.query_params.get("status")
		user_id = request.query_params.get("user_id")
		ticket_code = request.query_params.get("ticket_code")

		if event_id:
			if user_has_event_role(user, event_id, CHECKIN_ROLES):
				queryset = queryset.filter(registration__event_id=event_id)
			else:
				queryset = queryset.filter(
					registration__event_id=event_id, registration__user=user
				)
		else:
			queryset = queryset.filter(registration__user=user)

		if status_value:
			queryset = queryset.filter(status=status_value)
		if ticket_code:
			queryset = queryset.filter(ticket_code=ticket_code)
		if user_id and event_id and user_has_event_role(user, event_id, CHECKIN_ROLES):
			queryset = queryset.filter(registration__user_id=user_id)

		return queryset

	def get_serializer_class(self):  # type: ignore[override]
		if self.action == "list":
			return TicketListSerializer
		if self.action == "create":
			return TicketCreateSerializer
		if self.action in {"update", "partial_update"}:
			return TicketUpdateSerializer
		return TicketDetailSerializer

	def get_permissions(self):
		permissions: list[BasePermission] = [IsAuthenticated()]
		if self.action in {"create", "update", "partial_update", "destroy"}:
			permissions.append(IsEventHost())
		elif self.action == "retrieve":
			permissions.append(IsTicketOwnerOrOrganizer())
		return permissions


class CheckinScanAPIView(APIView):
	"""Scan a QR payload or ticket code and return check-in result."""

	permission_classes = [IsAuthenticated, IsEventCheckinStaff]

	def post(self, request):
		serializer = CheckinScanSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		data = cast(dict, serializer.validated_data)

		try:
			outcome = process_checkin_scan(
				event_id=data["event_id"],
				ticket_code=data.get("ticket_code"),
				qr_payload=data.get("qr_payload"),
				qr_signature=data.get("qr_signature"),
				scanner_user=request.user,
				note=data.get("note"),
			)
		except Event.DoesNotExist:
			return Response(
				{"detail": "Event not found."},
				status=status.HTTP_404_NOT_FOUND,
			)

		result = outcome["result"]
		log = outcome["log"]
		ticket = outcome["ticket"]
		registration = outcome["registration"]
		event = outcome["event"]

		response_payload = {
			"ok": result == "success",
			"result": result,
			"checked_in_at": log.checked_in_at,
			"ticket": None,
			"registration": None,
			"user": None,
			"event": {
				"id": event.id,
				"title": event.title,
			},
		}

		if ticket:
			response_payload["ticket"] = {
				"id": ticket.id,
				"ticket_code": ticket.ticket_code,
				"status": ticket.status,
			}
		if registration:
			response_payload["registration"] = {
				"id": registration.id,
				"status": registration.status,
			}
			response_payload["user"] = {
				"id": registration.user.id,
				"full_name": registration.user.full_name,
				"username": registration.user.username,
			}

		if result == "success":
			status_code = status.HTTP_200_OK
		elif result == "invalid_format":
			status_code = status.HTTP_400_BAD_REQUEST
		elif result == "invalid_ticket":
			status_code = status.HTTP_404_NOT_FOUND
		else:
			status_code = status.HTTP_409_CONFLICT

		return Response(response_payload, status=status_code)


class EventCohostCollectionAPIView(APIView):
	"""Manage event co-hosts for a specific event."""

	permission_classes = [IsAuthenticated, IsEventHostForEvent]

	def get(self, request, event_id):
		organizers = EventOrganizer.objects.select_related("user", "event").filter(
			event_id=event_id
		).exclude(organizer_role=EventOrganizer.OrganizerRole.OWNER)
		serializer = EventOrganizerSerializer(organizers, many=True)
		return Response(serializer.data)

	def post(self, request, event_id):
		serializer = EventCohostCreateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		data = cast(dict, serializer.validated_data)
		user_id = data["user_id"]
		organizer_role = data.get(
			"organizer_role", EventOrganizer.OrganizerRole.CO_HOST
		)

		event = get_object_or_404(Event, id=event_id)
		user = get_object_or_404(User, id=user_id)

		organizer, created = EventOrganizer.objects.get_or_create(
			event=event,
			user=user,
			defaults={"organizer_role": organizer_role},
		)

		if organizer.organizer_role == EventOrganizer.OrganizerRole.OWNER:
			raise ValidationError("Cannot modify owner role via this endpoint.")

		if not created and organizer.organizer_role != organizer_role:
			organizer.organizer_role = organizer_role
			organizer.save(update_fields=["organizer_role", "updated_at"])

		output = EventOrganizerSerializer(organizer)
		return Response(
			output.data,
			status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
		)


class EventCohostDetailAPIView(APIView):
	"""Update or remove a specific event co-host."""

	permission_classes = [IsAuthenticated, IsEventHostForEvent]

	def patch(self, request, event_id, user_id):
		serializer = EventCohostUpdateSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		organizer = get_object_or_404(
			EventOrganizer,
			event_id=event_id,
			user_id=user_id,
		)

		if organizer.organizer_role == EventOrganizer.OrganizerRole.OWNER:
			raise ValidationError("Cannot modify owner role via this endpoint.")

		data = cast(dict, serializer.validated_data)
		organizer.organizer_role = data["organizer_role"]
		organizer.save(update_fields=["organizer_role", "updated_at"])
		output = EventOrganizerSerializer(organizer)
		return Response(output.data)

	def delete(self, request, event_id, user_id):
		organizer = get_object_or_404(
			EventOrganizer,
			event_id=event_id,
			user_id=user_id,
		)

		if organizer.organizer_role == EventOrganizer.OrganizerRole.OWNER:
			raise ValidationError("Cannot delete owner role via this endpoint.")

		organizer.delete()
		return Response(status=status.HTTP_204_NO_CONTENT)
