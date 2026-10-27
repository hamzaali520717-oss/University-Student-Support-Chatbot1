from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.accounts import selectors as accounts_selectors


def student_required(view_func):
    @login_required(login_url="portal:login")
    @wraps(view_func)
    def _wrapped(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.user.role != request.user.Role.STUDENT:
            return render(request, "portal/not_authorized.html", status=403)
        # role == STUDENT is only the default; it doesn't guarantee a
        # StudentProfile row exists (e.g. an account made via createsuperuser
        # without going through apps.accounts.services.register_student).
        # Every portal view assumes a real profile, so gate on it here too.
        _, profile = accounts_selectors.get_current_user_profile(user=request.user)
        if profile is None:
            return render(request, "portal/not_authorized.html", status=403)
        return view_func(request, *args, **kwargs)

    return _wrapped
