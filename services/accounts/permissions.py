from rest_framework.permissions import BasePermission, IsAuthenticated


class IsOrgAdmin(BasePermission):
    message = "Org admin access required."

    def has_permission(self, request, view):
        return (
            IsAuthenticated().has_permission(request, view)
            and bool(request.user.is_staff)
        )
