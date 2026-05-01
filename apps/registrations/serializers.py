from django.utils import timezone
from rest_framework import serializers

from apps.events.models import EventOrganizer
from apps.registrations.models import EventRegistration, Ticket
from apps.registrations.services import (
	build_qr_payload,
	generate_ticket_code,
	sign_qr_payload,
)


class TicketListSerializer(serializers.ModelSerializer):
	registration_id = serializers.UUIDField(source="registration_id", read_only=True)
	event_id = serializers.UUIDField(source="registration.event_id", read_only=True)
	event_title = serializers.CharField(source="registration.event.title", read_only=True)
	user_id = serializers.UUIDField(source="registration.user_id", read_only=True)
	user_full_name = serializers.CharField(
		source="registration.user.full_name", read_only=True
	)

	class Meta:
		model = Ticket
		fields = [
			"id",
			"ticket_code",
			"status",
			"issued_at",
			"expires_at",
			"used_at",
			"registration_id",
			"event_id",
			"event_title",
			"user_id",
			"user_full_name",
		]
		read_only_fields = fields


class TicketDetailSerializer(serializers.ModelSerializer):
	registration_id = serializers.UUIDField(source="registration_id", read_only=True)
	registration_status = serializers.CharField(
		source="registration.status", read_only=True
	)
	event_id = serializers.UUIDField(source="registration.event_id", read_only=True)
	event_title = serializers.CharField(source="registration.event.title", read_only=True)
	user_id = serializers.UUIDField(source="registration.user_id", read_only=True)
	user_full_name = serializers.CharField(
		source="registration.user.full_name", read_only=True
	)

	class Meta:
		model = Ticket
		fields = [
			"id",
			"ticket_code",
			"qr_payload",
			"qr_signature",
			"status",
			"issued_at",
			"expires_at",
			"used_at",
			"registration_id",
			"registration_status",
			"event_id",
			"event_title",
			"user_id",
			"user_full_name",
		]
		read_only_fields = fields


class TicketCreateSerializer(serializers.ModelSerializer):
	registration_id = serializers.PrimaryKeyRelatedField(
		queryset=EventRegistration.objects.select_related("event", "user"),
		source="registration",
		write_only=True,
	)
	ticket_code = serializers.CharField(required=False, allow_blank=True)

	class Meta:
		model = Ticket
		fields = [
			"id",
			"registration_id",
			"ticket_code",
			"expires_at",
			"status",
			"issued_at",
			"qr_payload",
			"qr_signature",
		]
		read_only_fields = [
			"id",
			"status",
			"issued_at",
			"qr_payload",
			"qr_signature",
		]

	def validate_expires_at(self, value):
		if value and value <= timezone.now():
			raise serializers.ValidationError("expires_at must be in the future.")
		return value

	def validate(self, attrs):
		registration = attrs.get("registration")
		if Ticket.objects.filter(registration=registration).exists():
			raise serializers.ValidationError(
				{"registration_id": "Ticket already exists for this registration."}
			)
		if (
			registration.status
			!= EventRegistration.RegistrationStatus.REGISTERED
		):
			raise serializers.ValidationError(
				{"registration_id": "Registration is not eligible for ticketing."}
			)
		return attrs

	def create(self, validated_data):
		registration = validated_data["registration"]
		ticket_code = validated_data.pop("ticket_code", None)
		ticket_code = ticket_code or generate_ticket_code()
		expires_at = validated_data.get("expires_at") or registration.event.end_at
		qr_payload = build_qr_payload(ticket_code)
		qr_signature = sign_qr_payload(qr_payload)

		return Ticket.objects.create(
			registration=registration,
			ticket_code=ticket_code,
			qr_payload=qr_payload,
			qr_signature=qr_signature,
			status=Ticket.TicketStatus.VALID,
			expires_at=expires_at,
		)


class TicketUpdateSerializer(serializers.ModelSerializer):
	class Meta:
		model = Ticket
		fields = ["status", "expires_at", "used_at"]
		read_only_fields = ["used_at"]

	def validate_expires_at(self, value):
		if value and value <= timezone.now():
			raise serializers.ValidationError("expires_at must be in the future.")
		return value

	def update(self, instance, validated_data):
		status_value = validated_data.get("status")
		if status_value == Ticket.TicketStatus.USED and not instance.used_at:
			instance.used_at = timezone.now()
		return super().update(instance, validated_data)


class CheckinScanSerializer(serializers.Serializer):
	event_id = serializers.UUIDField()
	ticket_code = serializers.CharField(required=False, allow_blank=False)
	qr_payload = serializers.CharField(required=False, allow_blank=False)
	qr_signature = serializers.CharField(required=False, allow_blank=False)
	device_time = serializers.DateTimeField(required=False)
	note = serializers.CharField(required=False, allow_blank=True, allow_null=True)

	def validate(self, attrs):
		if not attrs.get("ticket_code") and not attrs.get("qr_payload"):
			raise serializers.ValidationError(
				"ticket_code or qr_payload is required."
			)
		if attrs.get("qr_payload") and not attrs.get("qr_signature"):
			raise serializers.ValidationError(
				"qr_signature is required when qr_payload is provided."
			)
		return attrs


class EventOrganizerSerializer(serializers.ModelSerializer):
	event_id = serializers.UUIDField(source="event_id", read_only=True)
	user_id = serializers.UUIDField(source="user_id", read_only=True)
	user_full_name = serializers.CharField(source="user.full_name", read_only=True)
	user_username = serializers.CharField(source="user.username", read_only=True)

	class Meta:
		model = EventOrganizer
		fields = [
			"id",
			"event_id",
			"user_id",
			"user_full_name",
			"user_username",
			"organizer_role",
			"joined_at",
		]
		read_only_fields = fields


class EventCohostCreateSerializer(serializers.Serializer):
	user_id = serializers.UUIDField()
	organizer_role = serializers.ChoiceField(
		choices=EventOrganizer.OrganizerRole.choices,
		required=False,
	)

	def validate_organizer_role(self, value):
		if value == EventOrganizer.OrganizerRole.OWNER:
			raise serializers.ValidationError("owner role cannot be assigned.")
		return value


class EventCohostUpdateSerializer(serializers.Serializer):
	organizer_role = serializers.ChoiceField(
		choices=EventOrganizer.OrganizerRole.choices
	)

	def validate_organizer_role(self, value):
		if value == EventOrganizer.OrganizerRole.OWNER:
			raise serializers.ValidationError("owner role cannot be assigned.")
		return value
