# permissions.py
from rest_framework.permissions import BasePermission

class IsRole(BasePermission):
    """
    Permission check for allowed roles.
    Add `allowed_roles` attribute to the view.
    """
    def has_permission(self, request, view):
        # Anonymous users can't access
        if not request.user or not request.user.is_authenticated:
            return False
        allowed_roles = getattr(view, 'allowed_roles', [])
        return request.user.role in allowed_roles