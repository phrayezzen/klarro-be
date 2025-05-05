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
        return hasattr(request.user, "recruiter")

    def has_object_permission(self, request, view, obj):
        is_staff = request.user.is_staff
        has_company = hasattr(obj, "company")
        has_flow = hasattr(obj, "flow") and obj.flow is not None

        if has_company:
            company = obj.company
            is_recruiter = company.recruiters.filter(
                id=request.user.recruiter.id
            ).exists()
        elif has_flow:
            company = obj.flow.company
            is_recruiter = company.recruiters.filter(
                id=request.user.recruiter.id
            ).exists()
        else:
            is_recruiter = False

        return is_staff or is_recruiter


class IsCompanyMember(permissions.BasePermission):
    """Check if the user is a member (admin or recruiter) of the company."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Get the company ID from the object
        if hasattr(obj, "company_id"):
            obj_company_id = obj.company_id
        elif hasattr(obj, "flow") and obj.flow:
            obj_company_id = obj.flow.company_id
        else:
            return False

        user_company_id = request.user.recruiter.company_id
        return obj_company_id == user_company_id


class IsFlowOwner(permissions.BasePermission):
    """
    Allows access only to recruiters who own the flow.
    """

    def has_object_permission(self, request, view, obj):
        return obj.recruiter_id == request.user.recruiter.id
