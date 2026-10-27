from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsOwnFeeStatus(BasePermission):
    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        student_profile = getattr(request.user, "student_profile", None)
        return bool(student_profile and obj.student_id == student_profile.id)
