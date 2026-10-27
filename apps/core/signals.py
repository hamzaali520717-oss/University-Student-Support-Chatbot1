from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate

ADMIN_STAFF_GROUP_NAME = "Admin Staff"

# Every app whose models a role=admin User should be able to manage through
# the admin site. Deliberately excludes django.contrib.auth (Group,
# Permission) so admin-role staff can manage domain data but not the
# permission system itself - that stays superuser-only.
ADMIN_MANAGED_APPS = [
    "accounts",
    "academics",
    "admissions",
    "finance",
    "content",
    "assistant",
]


def sync_admin_staff_group(**kwargs):
    """Keeps the "Admin Staff" group's permissions in sync with every
    permission Django has created for our own apps, so a new app/model
    automatically becomes manageable by role=admin users after its migration
    runs, with no separate step to remember. Runs on every post_migrate (once
    per app per `migrate` invocation); idempotent and cheap, so the redundant
    reruns within one `migrate` are harmless."""
    group, _ = Group.objects.get_or_create(name=ADMIN_STAFF_GROUP_NAME)
    group.permissions.set(Permission.objects.filter(content_type__app_label__in=ADMIN_MANAGED_APPS))


post_migrate.connect(sync_admin_staff_group, dispatch_uid="apps.core.sync_admin_staff_group")
