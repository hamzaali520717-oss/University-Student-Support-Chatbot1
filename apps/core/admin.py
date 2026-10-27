from unfold.sites import UnfoldAdminSite


class UniversityAdminSite(UnfoldAdminSite):
    def has_permission(self, request):
        from apps.accounts.models import User

        return super().has_permission(request) and (
            request.user.is_superuser or request.user.role == User.Role.ADMIN
        )
