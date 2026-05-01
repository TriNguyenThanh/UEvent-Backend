import hashlib
import hmac
import secrets

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.events.models import Event
from apps.registrations.models import CheckinLog, EventRegistration, Ticket, TicketQrToken

QR_PAYLOAD_PREFIX = "TICKET:"


def get_qr_secret() -> str:
	return getattr(settings, "TICKET_QR_SECRET", settings.SECRET_KEY)


def generate_ticket_code(prefix: str = "TK") -> str:
	while True:
		code = f"{prefix}-{secrets.token_hex(5).upper()}"
		if not Ticket.objects.filter(ticket_code=code).exists():
			return code


def build_qr_payload(ticket_code: str) -> str:
	return f"{QR_PAYLOAD_PREFIX}{ticket_code}"


def sign_qr_payload(payload: str) -> str:
	secret = get_qr_secret().encode("utf-8")
	return hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_qr_signature(payload: str, signature: str | None) -> bool:
	if not signature:
		return False
	expected = sign_qr_payload(payload)
	return hmac.compare_digest(expected, signature)


def hash_token(token: str) -> str:
	return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _resolve_ticket_from_payload(qr_payload: str, now):
	payload_value = qr_payload
	if qr_payload.startswith(QR_PAYLOAD_PREFIX):
		payload_value = qr_payload[len(QR_PAYLOAD_PREFIX) :]

	token_hash = hash_token(payload_value)
	token = (
		TicketQrToken.objects.select_related(
			"ticket",
			"ticket__registration",
			"ticket__registration__event",
			"ticket__registration__user",
		)
		.filter(token_hash=token_hash, valid_from__lte=now, valid_to__gte=now)
		.first()
	)
	if token:
		return Ticket.objects.select_for_update().select_related(
			"registration",
			"registration__event",
			"registration__user",
		).get(id=token.ticket.id)

	return Ticket.lock_for_checkin(payload_value)


def process_checkin_scan(
	*,
	event_id,
	ticket_code: str | None,
	qr_payload: str | None,
	qr_signature: str | None,
	scanner_user=None,
	note: str | None = None,
):
	now = timezone.now()
	event = Event.objects.get(id=event_id)
	ticket = None
	registration = None
	result = None

	with transaction.atomic():
		if qr_payload:
			if not verify_qr_signature(qr_payload, qr_signature or ""):
				result = CheckinLog.CheckinResult.INVALID_FORMAT
			else:
				try:
					ticket = _resolve_ticket_from_payload(qr_payload, now)
				except Ticket.DoesNotExist:
					ticket = None
		elif ticket_code:
			try:
				ticket = Ticket.lock_for_checkin(ticket_code)
			except Ticket.DoesNotExist:
				ticket = None

		if result is None:
			if not ticket:
				result = CheckinLog.CheckinResult.INVALID_TICKET
			else:
				registration = ticket.registration
				if registration.event_id != event.id:
					result = CheckinLog.CheckinResult.INVALID_TICKET
				elif event.status != Event.Status.ACTIVE:
					result = CheckinLog.CheckinResult.EVENT_UNAVAILABLE
				elif event.start_at and event.start_at > now:
					result = CheckinLog.CheckinResult.EVENT_UNAVAILABLE
				elif event.end_at and event.end_at < now:
					result = CheckinLog.CheckinResult.EVENT_UNAVAILABLE
				elif ticket.status == Ticket.TicketStatus.USED or (
					registration.status
					== EventRegistration.RegistrationStatus.CHECKED_IN
				):
					result = CheckinLog.CheckinResult.ALREADY_CHECKED_IN
				elif ticket.status in {
					Ticket.TicketStatus.CANCELLED,
					Ticket.TicketStatus.EXPIRED,
				}:
					result = CheckinLog.CheckinResult.INVALID_TICKET
				elif registration.status in {
					EventRegistration.RegistrationStatus.CANCELLED,
					EventRegistration.RegistrationStatus.REJECTED,
				}:
					result = CheckinLog.CheckinResult.INVALID_TICKET
				elif ticket.expires_at and ticket.expires_at <= now:
					if ticket.status == Ticket.TicketStatus.VALID:
						ticket.status = Ticket.TicketStatus.EXPIRED
						ticket.save(update_fields=["status", "updated_at"])
					result = CheckinLog.CheckinResult.INVALID_TICKET
				else:
					ticket.status = Ticket.TicketStatus.USED
					ticket.used_at = now
					ticket.save(update_fields=["status", "used_at", "updated_at"])
					if (
						registration.status
						!= EventRegistration.RegistrationStatus.CHECKED_IN
					):
						registration.status = (
							EventRegistration.RegistrationStatus.CHECKED_IN
						)
						registration.save(update_fields=["status", "updated_at"])
					result = CheckinLog.CheckinResult.SUCCESS

		log = CheckinLog.objects.create(
			event=event,
			ticket=ticket,
			scanner_user=scanner_user,
			checked_in_at=now,
			result=result,
			note=note,
		)

	return {
		"result": result,
		"log": log,
		"ticket": ticket,
		"registration": registration,
		"event": event,
	}
