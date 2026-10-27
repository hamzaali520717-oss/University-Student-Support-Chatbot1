import re

from apps.academics import selectors as academics_selectors
from apps.accounts.models import StudentProfile
from apps.admissions import selectors as admissions_selectors
from apps.assistant.services.answering import Answer
from apps.finance import selectors as finance_selectors

# Checked in this fixed order - first keyword match wins. Deliberately simple:
# false negatives here just fall through to apps/portal/views.py::ask's general
# RAG path with the actual is_personal_question signal, so a miss here can
# under-trigger a template answer (falls back to an LLM call, or an honest
# decline if nothing grounds it) but can never leak personal data - it's
# purely a completeness/UX concern, not a safety one. "program_subjects" is
# checked before "enrollments" and "program" since it shares vocabulary with
# both ("my program", "subjects") but is a distinct, more specific question.
INTENT_KEYWORDS: dict[str, list[str]] = {
    "fees": ["fee", "fees", "tuition", "balance", "amount due", "paid", "payment", "owe"],
    "attendance": ["attendance", "present", "absent", "miss", "missed"],
    "program_subjects": [
        "subjects are in my program",
        "subjects in my program",
        "subjects does my program",
        "subjects for my program",
        "courses are in my program",
        "courses in my program",
        "courses for my program",
        "curriculum",
    ],
    "enrollments": [
        "enrolled",
        "my courses",
        "my classes",
        "my subjects",
        "which subjects",
        "what am i taking",
    ],
    "semester_plan": ["semester plan", "my plan", "planned subjects"],
    "deadline": ["deadline", "due date", "last date"],
    "program": ["my program", "which program", "what program"],
    "department": ["my department", "which department", "what department"],
    "registration_no": [
        "registration number",
        "registration no",
        "reg no",
        "reg. no",
        "student id",
        "my id",
    ],
    "current_semester": [
        "what semester am i",
        "which semester am i",
        "my semester",
        "my current semester",
    ],
}


def detect_intent(question: str) -> str | None:
    lowered = question.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if re.search(rf"\b{re.escape(keyword)}\b", lowered):
                return intent
    return None


def _answer_fees(student: StudentProfile) -> str:
    statuses = list(finance_selectors.list_student_fee_statuses(student=student))
    if not statuses:
        return "You don't have any fee records yet."
    outstanding = [
        status for status in statuses if finance_selectors.fee_status_outstanding(status) > 0
    ]
    if not outstanding:
        return "You have no outstanding fees - all paid up."
    total_due = sum(finance_selectors.fee_status_outstanding(status) for status in outstanding)
    lines = [
        f"Your outstanding balance is PKR {total_due:,.0f} across {len(outstanding)} semester(s)."
    ]
    lines += [
        f"Semester {status.semester}: PKR {finance_selectors.fee_status_outstanding(status):,.0f} "
        f"due ({status.get_status_display()})."
        for status in outstanding
    ]
    return " ".join(lines)


def _answer_attendance(student: StudentProfile) -> str:
    records = list(academics_selectors.list_student_attendance(student=student))
    summary = academics_selectors.summarize_attendance(records)
    if summary["total"] == 0:
        return "You don't have any attendance records yet."
    return (
        f"You've attended {summary['present']} of {summary['total']} recorded classes "
        f"({summary['rate']}%)."
    )


def _answer_enrollments(student: StudentProfile) -> str:
    enrollments = list(academics_selectors.list_student_enrollments(student=student))
    if not enrollments:
        return "You're not enrolled in any subjects yet."
    subjects = ", ".join(f"{e.subject.course.code} {e.subject.course.title}" for e in enrollments)
    return f"You're enrolled in: {subjects}."


def _answer_semester_plan(student: StudentProfile) -> str:
    plans = list(academics_selectors.list_student_semester_plans(student=student))
    if not plans:
        return "You don't have a semester plan yet."
    lines = [
        f"Semester {plan.semester}: {', '.join(s.course.code for s in plan.subjects.all())}."
        for plan in plans
    ]
    return "Your semester plan - " + " ".join(lines)


def _answer_deadline(student: StudentProfile) -> str:
    deadlines = list(
        admissions_selectors.list_upcoming_deadlines(program_code=student.program.code)
    )
    if not deadlines:
        return "There are no upcoming deadlines for your program right now."
    nearest = deadlines[0]
    return f"Your next deadline is {nearest.label} on {nearest.date:%B %d, %Y}."


def _answer_program_subjects(student: StudentProfile) -> str:
    subjects = list(academics_selectors.list_subjects(program_code=student.program.code))
    if not subjects:
        return f"No subjects are on record for your program ({student.program.name})."
    listed = ", ".join(
        f"{subject.course.code} {subject.course.title} (semester {subject.semester})"
        for subject in subjects
    )
    return f"Subjects in {student.program.name} ({student.program.code}): {listed}."


def _answer_program(student: StudentProfile) -> str:
    return f"You're enrolled in {student.program.name} ({student.program.code})."


def _answer_department(student: StudentProfile) -> str:
    department = student.program.department
    return f"Your program ({student.program.name}) is offered by {department.name}."


def _answer_registration_no(student: StudentProfile) -> str:
    return f"Your registration number is {student.registration_no}."


def _answer_current_semester(student: StudentProfile) -> str:
    enrollments = list(academics_selectors.list_student_enrollments(student=student))
    if not enrollments:
        return "You don't have any enrollments yet, so I can't tell which semester you're in."
    semester = max(enrollment.subject.semester for enrollment in enrollments)
    return f"Based on your current enrollments, you're in semester {semester}."


_BUILDERS = {
    "fees": _answer_fees,
    "attendance": _answer_attendance,
    "program_subjects": _answer_program_subjects,
    "enrollments": _answer_enrollments,
    "semester_plan": _answer_semester_plan,
    "deadline": _answer_deadline,
    "program": _answer_program,
    "department": _answer_department,
    "registration_no": _answer_registration_no,
    "current_semester": _answer_current_semester,
}


def answer_personal_intent(*, intent: str, student: StudentProfile) -> Answer:
    text = _BUILDERS[intent](student)
    return Answer(text=text, sources=[], grounded=True)
