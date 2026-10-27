from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.db import transaction

from apps.academics.models import Program
from apps.accounts.models import AdminProfile, StudentProfile, User
from apps.core.signals import ADMIN_STAFF_GROUP_NAME


@transaction.atomic
def bootstrap_admin(*, username: str, email: str, password: str) -> User:
    """Creates (or promotes) the first admin account from env-supplied
    credentials, for platforms with no interactive shell for createsuperuser.
    Safe to rerun as a Render one-off job/preDeployCommand: an existing user
    is (re)promoted to role=admin and re-synced, but its password is left
    untouched so a later credential rotation can't be undone by rerunning
    this."""
    user, created = User.objects.get_or_create(
        username=username, defaults={"email": email, "role": User.Role.ADMIN}
    )
    if created:
        validate_password(password, user=user)
        user.set_password(password)
    user.role = User.Role.ADMIN
    user.email = email
    user.save()
    sync_admin_access(user=user)
    return user


@transaction.atomic
def register_student(
    *,
    username: str,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    registration_no: str,
    program: Program,
) -> User:
    user = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=User.Role.STUDENT,
    )
    validate_password(password, user=user)
    user.set_password(password)
    user.save()
    StudentProfile.objects.create(user=user, registration_no=registration_no, program=program)
    return user


@transaction.atomic
def sync_admin_access(*, user: User) -> None:
    """Keeps is_staff and "Admin Staff" group membership in sync with a
    User's role - role=admin gets full admin-site access via the group
    rather than is_superuser, so permissions stay inspectable/revocable
    through the normal Django permission system instead of an unconditional
    bypass. Safe to call on every save regardless of whether role actually
    changed; idempotent. Wrapped in one transaction so a failure partway
    through (e.g. creating the group or profile) can't leave is_staff
    flipped with no matching group membership."""
    group, _ = Group.objects.get_or_create(name=ADMIN_STAFF_GROUP_NAME)
    if user.role == User.Role.ADMIN:
        user.is_staff = True
        user.groups.add(group)
        AdminProfile.objects.get_or_create(user=user)
    else:
        user.is_staff = False
        user.groups.remove(group)
    user.save(update_fields=["is_staff"])
