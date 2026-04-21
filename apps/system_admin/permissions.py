from rest_framework.permissions import BasePermission

class IsSystemAdmin(BasePermission):
    msg = 'You do not have permission to access this resource. System Admins only.' 

    def has_permission(self, request, view):
        return True
        return request.user and request.user.is_authenticated and request.user.is_superuser
    