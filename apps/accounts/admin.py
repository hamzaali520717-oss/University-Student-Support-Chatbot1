from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.exceptions import ValidationError
from unfold.admin import ModelAdmin, StackedInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from apps.accounts import services
from apps.accounts.models import StudentProfile, User


class StudentProfileInline(StackedInline):
    model = StudentProfile
    fk_name = "user"
    extra = 1
    max_num = 1
    fields = ["registration_no", "program"]
    autocomplete_fields = ["program"]


@admin.register(StudentProfile)
class StudentProfileAdmin(ModelAdmin):
    list_display = ["registration_no", "user", "program"]
    list_filter = ["program"]
    search_fields = ["registration_no", "user__username", "user__first_name", "user__last_name"]
    autocomplete_fields = ["user", "program"]


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    inlines = [StudentProfileInline]

    fieldsets = BaseUserAdmin.fieldsets + (("Role", {"fields": ("role",)}),)
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2", "role"),
            },
        ),
    )

    list_display = ["username", "first_name", "last_name", "email", "role", "is_active"]
    list_filter = ["role", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name"]

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        # Only a superuser may grant Django's own permission machinery -
        # role=admin access is meant to run entirely through the "Admin
        # Staff" group (see apps.accounts.services.sync_admin_access), never
        # through is_staff/is_superuser/groups edited directly, or any
        # Admin Staff member could grant themselves superuser via this form.
        if not request.user.is_superuser:
            readonly += ["is_staff", "is_superuser", "groups", "user_permissions"]
        return readonly

    def _blocked_for_non_superuser(self, request, obj) -> bool:
        # get_readonly_fields above stops an Admin Staff member from ticking
        # is_superuser on their own account via this form, but that's not
        # the only door: Django's stock user_change_password view resolves
        # its target through get_object()/has_change_permission() same as
        # the change form, so without this, any account holding
        # accounts.change_user (i.e. every Admin Staff member - see
        # apps.core.signals.ADMIN_MANAGED_APPS) could open an *existing*
        # superuser's change-password form directly and reset their
        # password, hijacking that superuser account instead of granting
        # itself the flag outright.
        return bool(obj is not None and obj.is_superuser and not request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        if self._blocked_for_non_superuser(request, obj):
            return False
        return super().has_view_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if self._blocked_for_non_superuser(request, obj):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if self._blocked_for_non_superuser(request, obj):
            return False
        return super().has_delete_permission(request, obj)

    def get_queryset(self, request):
        # Keeps superuser accounts off the changelist for non-superusers,
        # matching the has_*_permission denials above so a hidden account
        # doesn't linger as a visible-but-inert row.
        queryset = super().get_queryset(request)
        if not request.user.is_superuser:
            queryset = queryset.filter(is_superuser=False)
        return queryset

    def get_object(self, request, object_id, from_field=None):
        # get_queryset() above hides superusers from the changelist for
        # non-superusers, but get_object() backs the change, delete, and
        # password views too (Django's user_change_password looks the
        # target up the same way). If it reused that filter, a direct URL
        # to a hidden superuser would resolve to None and those views would
        # 404 - "not found" - instead of reaching has_change_permission()/
        # has_delete_permission() with the real object and 403ing
        # explicitly. Look the object up against the queryset one level up
        # the MRO (bypassing our own get_queryset override, not Django's)
        # so the permission checks above always see the real object.
        queryset = super().get_queryset(request)
        model = queryset.model
        field = model._meta.pk if from_field is None else model._meta.get_field(from_field)
        try:
            object_id = field.to_python(object_id)
            return queryset.get(**{field.name: object_id})
        except (model.DoesNotExist, ValidationError, ValueError):
            return None

    def save_related(self, request, form, formsets, change):
        # sync_admin_access must run after super().save_related(), not from
        # save_model(): Django defers the "groups" M2M save to
        # form.save_m2m() inside save_related(), which runs *after*
        # save_model() and would silently overwrite whatever group
        # membership was just set there (e.g. for a superuser request, where
        # "groups" is still an editable field on the form).
        super().save_related(request, form, formsets, change)
        services.sync_admin_access(user=form.instance)

    def _warn_if_student_missing_profile(self, request, obj):
        if obj.role == User.Role.STUDENT and not StudentProfile.objects.filter(user=obj).exists():
            messages.error(
                request,
                "This student has no profile yet — student portal features will not work "
                "until you add a registration number and program in the Student Profile "
                "section below.",
            )

    def response_add(self, request, obj, post_url_continue=None):
        self._warn_if_student_missing_profile(request, obj)
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        self._warn_if_student_missing_profile(request, obj)
        return super().response_change(request, obj)
