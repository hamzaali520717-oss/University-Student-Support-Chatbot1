from django.db.models import QuerySet

from apps.accounts.models import AdminProfile, StudentProfile, User


def list_users() -> QuerySet[User]:
    return User.objects.all().order_by("id")


def get_current_user_profile(*, user: User) -> tuple[User, StudentProfile | AdminProfile | None]:
    if user.role == User.Role.STUDENT:
        profile = StudentProfile.objects.select_related("program").filter(user=user).first()
    elif user.role == User.Role.ADMIN:
        profile = AdminProfile.objects.filter(user=user).first()
    else:
        profile = None
    return user, profile
