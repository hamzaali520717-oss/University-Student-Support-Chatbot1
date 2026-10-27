import math

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from rest_framework.throttling import ScopedRateThrottle

from apps.academics import selectors as academics_selectors
from apps.academics import services as academics_services
from apps.academics.models import Attendance
from apps.accounts import selectors as accounts_selectors
from apps.assistant.services import answering
from apps.content import selectors as content_selectors
from apps.finance import selectors as finance_selectors
from apps.finance.models import FeeStatus
from apps.portal import intents
from apps.portal.forms import StudentAuthenticationForm
from apps.portal.permissions import student_required

RING_RADIUS = 54
RING_CIRCUMFERENCE = 2 * math.pi * RING_RADIUS
ATTENDANCE_GOOD_THRESHOLD = 75

FEE_STATUS_LABELS = {
    FeeStatus.Status.PAID: "Paid in full",
    FeeStatus.Status.PARTIAL: "Partial",
    FeeStatus.Status.UNPAID: "Unpaid",
}


def _safe_next_url(request: HttpRequest) -> str | None:
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return next_url
    return None


class _LoginThrottleScope:
    """Stands in for the APIView ScopedRateThrottle expects - it only ever
    reads `.throttle_scope` - so this plain Django view can share the same
    "login" rate limit (settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"])
    as the JWT login/refresh views instead of going unthrottled."""

    throttle_scope = "login"


_LOGIN_THROTTLE_VIEW = _LoginThrottleScope()


def _login_rate_limited(request: HttpRequest) -> bool:
    return not ScopedRateThrottle().allow_request(request, _LOGIN_THROTTLE_VIEW)


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("portal:dashboard")

    if request.method == "POST":
        if _login_rate_limited(request):
            # An unbound form (no `data=`) deliberately never runs
            # AuthenticationForm.clean() - which calls authenticate() and
            # does real password hashing - so a throttled request doesn't
            # still pay that cost. add_error() expects a form that's been
            # through full_clean() at least once (it reads self.cleaned_data),
            # which full_clean() never populates for an unbound form; seed
            # an empty dict rather than binding it with the submitted data.
            form = StudentAuthenticationForm(request)
            form.cleaned_data = {}
            form.add_error(None, "Too many login attempts. Please try again later.")
            return render(
                request,
                "portal/login.html",
                {"form": form, "next": request.POST.get("next", "")},
                status=429,
            )
        form = StudentAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect(_safe_next_url(request) or "portal:dashboard")
    else:
        form = StudentAuthenticationForm(request)

    return render(request, "portal/login.html", {"form": form, "next": request.GET.get("next", "")})


@require_POST
@login_required(login_url="portal:login")
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("portal:login")


def _attendance_ring_context(records: list[Attendance]) -> dict:
    summary = academics_selectors.summarize_attendance(records)
    if summary["total"] == 0:
        return {"has_data": False}
    rate = summary["rate"]
    status = "good" if rate >= ATTENDANCE_GOOD_THRESHOLD else "attention"
    return {
        "has_data": True,
        "rate": rate,
        "status": status,
        "status_label": "On track" if status == "good" else "Needs attention",
        "circumference": round(RING_CIRCUMFERENCE, 2),
        "dashoffset": round(RING_CIRCUMFERENCE * (1 - rate / 100), 2),
    }


def _fee_progress_context(fee_statuses: list[FeeStatus]) -> dict:
    if not fee_statuses:
        return {"has_data": False}
    current = max(fee_statuses, key=lambda status: status.semester)
    percent_paid = 0
    if current.amount_due:
        percent_paid = min(100, round(current.amount_paid / current.amount_due * 100))
    status = "good" if finance_selectors.is_fee_status_settled(current) else "attention"
    return {
        "has_data": True,
        "fee_status": current,
        "percent_paid": percent_paid,
        "status": status,
        "status_label": FEE_STATUS_LABELS[current.status],
    }


@student_required
def dashboard(request: HttpRequest) -> HttpResponse:
    _, student = accounts_selectors.get_current_user_profile(user=request.user)

    enrollments = list(academics_selectors.list_student_enrollments(student=student))
    attendance_records = list(academics_selectors.list_student_attendance(student=student))
    fee_statuses = list(finance_selectors.list_student_fee_statuses(student=student))
    announcements = list(
        content_selectors.list_published_announcements(audiences=["public", "student"])
    )[:4]

    context = {
        "enrollment_count": len(enrollments),
        "attendance": _attendance_ring_context(attendance_records),
        "fee": _fee_progress_context(fee_statuses),
        "announcements": announcements,
    }
    return render(request, "portal/dashboard.html", context)


@student_required
def enrollments(request: HttpRequest) -> HttpResponse:
    _, student = accounts_selectors.get_current_user_profile(user=request.user)

    if request.method == "POST":
        try:
            subject_id = int(request.POST.get("subject", ""))
        except (TypeError, ValueError):
            raise Http404
        subject = get_object_or_404(
            academics_selectors.list_subjects(program_code=student.program.code), id=subject_id
        )
        try:
            academics_services.enroll_student(student=student, subject=subject)
        except ValidationError as exc:
            messages.error(request, exc.message)
        else:
            messages.success(request, f"Enrolled in {subject.course.code} {subject.course.title}.")
        return redirect("portal:enrollments")

    current = list(academics_selectors.list_student_enrollments(student=student))
    enrolled_subject_ids = {enrollment.subject_id for enrollment in current}
    available_subjects = [
        subject
        for subject in academics_selectors.list_subjects(program_code=student.program.code)
        if subject.id not in enrolled_subject_ids
    ]
    context = {"enrollments": current, "available_subjects": available_subjects}
    return render(request, "portal/enrollments.html", context)


@student_required
def attendance(request: HttpRequest) -> HttpResponse:
    _, student = accounts_selectors.get_current_user_profile(user=request.user)
    raw_subject_id = request.GET.get("subject")
    try:
        subject_id = int(raw_subject_id) if raw_subject_id else None
    except (TypeError, ValueError):
        subject_id = None
    records = academics_selectors.list_student_attendance(student=student, subject_id=subject_id)
    return render(request, "portal/attendance.html", {"attendance_records": records})


@student_required
def semester_plan(request: HttpRequest) -> HttpResponse:
    _, student = accounts_selectors.get_current_user_profile(user=request.user)
    plans = academics_selectors.list_student_semester_plans(student=student)
    return render(request, "portal/semester_plan.html", {"plans": plans})


@student_required
def fees(request: HttpRequest) -> HttpResponse:
    _, student = accounts_selectors.get_current_user_profile(user=request.user)
    fee_statuses = finance_selectors.list_student_fee_statuses(student=student)
    return render(request, "portal/fees.html", {"fee_statuses": fee_statuses})


@student_required
def announcements(request: HttpRequest) -> HttpResponse:
    items = list(
        content_selectors.list_published_announcements(audiences=["public", "student"])
    )
    return render(request, "portal/announcement_list.html", {"announcements": items})


@student_required
@require_POST
def ask(request: HttpRequest) -> HttpResponse:
    question = request.POST.get("question", "").strip()
    if not question or len(question) > 2000:
        return render(
            request,
            "portal/_ask_turn.html",
            {"question": question, "error": "Please enter a question (up to 2000 characters)."},
        )

    _, student = accounts_selectors.get_current_user_profile(user=request.user)
    intent = intents.detect_intent(question)
    if intent is not None:
        # One of the 5 specific template-answerable buckets - answered
        # entirely from selectors, no LLM call at all.
        answer = intents.answer_personal_intent(intent=intent, student=student)
    else:
        # Not a specific bucket, but may still be personal in nature (e.g.
        # "what subjects are in my program?") - answering.answer_question
        # only attaches build_student_context when include_personal_context
        # is True, and deterministically returns the honest I_DONT_KNOW
        # fallback when there's neither a public-KB match nor a personal
        # signal, so a router miss can never silently become a confident
        # answer grounded in nothing.
        answer = answering.answer_question(
            question=question,
            student=student,
            include_personal_context=answering.is_personal_question(question),
        )

    return render(request, "portal/_ask_turn.html", {"question": question, "answer": answer})
