from dataclasses import dataclass

from apps.academics import selectors as academics_selectors
from apps.accounts.models import StudentProfile
from apps.finance import selectors as finance_selectors


@dataclass(frozen=True)
class StudentContext:
    text: str
    label: str = "Your student record"


def build_student_context(*, student: StudentProfile) -> StudentContext:
    """Assembles a student's own record live from existing selectors. Nothing
    here is embedded or persisted; it exists only for the duration of one
    request and is scoped strictly to the given student."""
    lines = [f"Student: {student.registration_no} ({student.program.code})"]

    enrollments = list(academics_selectors.list_student_enrollments(student=student))
    if enrollments:
        lines.append("Enrollments:")
        lines += [
            f"- {e.subject.course.code} {e.subject.course.title} (semester {e.subject.semester})"
            for e in enrollments
        ]
    else:
        lines.append("Enrollments: none on record.")

    attendance = list(academics_selectors.list_student_attendance(student=student))
    if attendance:
        by_course: dict[str, list] = {}
        for record in attendance:
            by_course.setdefault(record.enrollment.subject.course.code, []).append(record)
        lines.append("Attendance (present/total):")
        for code, records in by_course.items():
            summary = academics_selectors.summarize_attendance(records)
            lines.append(f"- {code}: {summary['present']}/{summary['total']}")
    else:
        lines.append("Attendance: no records.")

    plans = list(academics_selectors.list_student_semester_plans(student=student))
    if plans:
        lines.append("Semester plans:")
        for plan in plans:
            subjects = ", ".join(s.course.code for s in plan.subjects.all())
            lines.append(f"- Semester {plan.semester}: {subjects}")

    fee_statuses = list(finance_selectors.list_student_fee_statuses(student=student))
    if fee_statuses:
        lines.append("Fee status:")
        lines += [
            f"- Semester {fee.semester}: due {fee.amount_due}, paid {fee.amount_paid} ({fee.status})"
            for fee in fee_statuses
        ]
    else:
        lines.append("Fee status: no records.")

    return StudentContext(text="\n".join(lines))
