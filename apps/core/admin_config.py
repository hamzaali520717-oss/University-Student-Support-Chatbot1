from django.contrib.admin.apps import AdminConfig


class UniversityAdminConfig(AdminConfig):
    default_site = "apps.core.admin.UniversityAdminSite"
