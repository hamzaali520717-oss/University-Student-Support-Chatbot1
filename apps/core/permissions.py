from django.contrib.auth import get_user_model
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsStudent(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.role == get_user_model().Role.STUDENT
        )


class IsAdminStaff(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.role == get_user_model().Role.ADMIN or user.is_superuser)
        )


class IsAdminOrReadOnly(IsAdminStaff):
    """Public catalog data (fee structures, admission requirements/deadlines,
    scholarships) is intentionally readable by anyone, authenticated or not -
    it's the same public data the website already renders via selectors, just
    exposed as an API. Writes require the same admin check as IsAdminStaff
    (role=admin or is_superuser), kept in one place so this and IsAdminStaff
    can't drift apart on what "admin" means."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        return request.method in SAFE_METHODS or super().has_permission(request, view)


class IsAuthenticatedReadOnly(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.method in SAFE_METHODS
        )
