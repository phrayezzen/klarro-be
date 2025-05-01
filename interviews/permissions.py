from rest_framework import permissions


class IsCompanyAdmin(permissions.BasePermission):
    """Check if the user is an admin of the company."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or (
            hasattr(obj, "company") and request.user in obj.company.admins.all()
        )


class IsRecruiter(permissions.BasePermission):
    """Check if the user is a recruiter of the company."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or (
            hasattr(obj, "company") and request.user in obj.company.recruiters.all()
        )


class IsCompanyMember(permissions.BasePermission):
    """Check if the user is a member (admin or recruiter) of the company."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        if not hasattr(obj, "company"):
            return False
        return (
            request.user in obj.company.admins.all()
            or request.user in obj.company.recruiters.all()
        )


class IsFlowOwner(permissions.BasePermission):
    """
    Allows access only to recruiters who own the flow.
    """

    def has_object_permission(self, request, view, obj):
        return obj.recruiter_id == request.user.recruiter.id
