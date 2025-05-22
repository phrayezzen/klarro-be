from rest_framework import permissions

from .models import Candidate, Company, Interview, Step


class IsCompanyAdmin(permissions.BasePermission):
    """Check if the user is an admin of the company."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if not hasattr(request.user, "recruiter"):
            return False

        return request.user.is_staff or request.user.recruiter.is_admin

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if not hasattr(request.user, "recruiter"):
            return False

        if request.user.is_staff:
            return True

        # Get the company ID from the object
        if hasattr(obj, "company_id"):
            obj_company_id = obj.company_id
        elif hasattr(obj, "flow") and obj.flow:
            obj_company_id = obj.flow.company_id
        else:
            return False

        user_company_id = request.user.recruiter.company_id
        return obj_company_id == user_company_id and request.user.recruiter.is_admin


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
        elif hasattr(obj, "candidate") and hasattr(obj.candidate, "flow"):
            # Special case for Interview objects
            company = obj.candidate.flow.company
            is_recruiter = company.recruiters.filter(
                id=request.user.recruiter.id
            ).exists()
        else:
            is_recruiter = False

        return is_staff or is_recruiter


class IsCompanyMember(permissions.BasePermission):
    """Check if the user is a member (admin or recruiter) of the company."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if not hasattr(request.user, "recruiter"):
            return False

        # For list/create actions, check if company_id in query params matches user's company
        company_id = None
        if hasattr(request, "query_params"):
            company_id = request.query_params.get("company_id")
        elif hasattr(request, "GET"):
            company_id = request.GET.get("company_id")

        if company_id:
            try:
                company_id = int(company_id)
                return company_id == request.user.recruiter.company_id
            except (ValueError, TypeError):
                return False

        return True

    def has_object_permission(self, request, view, obj):
        from .models import Candidate, Company, Interview, Step

        if hasattr(obj, "company_id"):
            obj_company_id = obj.company_id
        elif hasattr(obj, "flow") and obj.flow:
            obj_company_id = obj.flow.company_id
        elif isinstance(obj, Company):
            obj_company_id = obj.id
        elif isinstance(obj, Step):
            obj_company_id = obj.flow.company_id
        elif isinstance(obj, Candidate):
            obj_company_id = obj.flow.company_id
        elif isinstance(obj, Interview):
            obj_company_id = obj.candidate.flow.company_id
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
