from rest_framework.permissions import BasePermission


class IsRegistrationOwner(BasePermission):
    message = "You do not have access to this registration."

    def has_object_permission(self, request, view, obj):  # type: ignore[override]
        return bool(request.user and request.user.is_authenticated and obj.user_id == request.user.id)
