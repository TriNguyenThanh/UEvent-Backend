from django.db import models
from common.models import BaseModel


class EventInvitation(BaseModel):
    class InvitationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        EXPIRED = "expired", "Expired"

    class InviteChannel(models.TextChoices):
        EMAIL = "email", "Email"
        CONTACT = "contact", "Contact"
        LINK = "link", "Link"

    event = models.ForeignKey("events.Event", on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField() # Deprecated -> move to invite_target
    invited_user = models.ForeignKey( # Deprecated
        "users.User",
        on_delete=models.SET_NULL,
        related_name="old_event_invitations",
        blank=True,
        null=True,
    )
    token = models.CharField(max_length=255, unique=True) # Deprecated
    expires_at = models.DateTimeField(blank=True, null=True) # Deprecated
    
    # New fields (Dual-write refactor)
    inviter_user = models.ForeignKey(
        "users.User", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='sent_invitations'
    )
    invite_channel = models.CharField(max_length=20, choices=InviteChannel.choices, default=InviteChannel.EMAIL)
    invite_target = models.CharField(max_length=255, blank=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    responded_at = models.DateTimeField(blank=True, null=True)

    status = models.CharField(max_length=20, choices=InvitationStatus.choices, default=InvitationStatus.PENDING)

    class Meta(BaseModel.Meta):
        db_table = "event_invitations"
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["event", "email"], name="uq_event_invites_event_email")]
        indexes = [models.Index(fields=["event", "status"]), models.Index(fields=["email"])]

    def __str__(self):
        return f"{self.event} -> {self.email}"

