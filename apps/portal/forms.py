from django import forms
from django.contrib.auth.forms import AuthenticationForm

from apps.accounts.models import User

TEXT_INPUT_CLASSES = (
    "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm "
    "focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
)
# Same as TEXT_INPUT_CLASSES, with room on the right for the show/hide
# password toggle button (see portal/login.html) so typed text never runs
# under it.
PASSWORD_INPUT_CLASSES = TEXT_INPUT_CLASSES + " pr-10"


class StudentAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs["class"] = TEXT_INPUT_CLASSES
        self.fields["password"].widget.attrs["class"] = PASSWORD_INPUT_CLASSES

    def confirm_login_allowed(self, user: User) -> None:
        super().confirm_login_allowed(user)
        if user.role != User.Role.STUDENT:
            raise forms.ValidationError(
                "This portal is for students only. Admin staff should use /admin/.",
                code="not_a_student",
            )
