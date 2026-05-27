from rest_framework.permissions import BasePermission, SAFE_METHODS

from apps.events.models import EventOrganizer


class IsInteractionOwner(BasePermission):
    message = "You do not have access to this interaction."

    def has_object_permission(self, request, view, obj):  # type: ignore[override]
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if obj.user_id == user.id or user.is_superuser:
            return True
        return EventOrganizer.objects.filter(event=obj.event, user=user).exists()
