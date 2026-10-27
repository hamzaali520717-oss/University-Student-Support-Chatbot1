import datetime

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.academics.models import Attendance, Course, Department, Enrollment, Program, Subject
from apps.academics.services import enroll_student, record_attendance
from apps.accounts.models import StudentProfile, User
from apps.accounts.services import register_student
from apps.assistant.services.catalog import suppress_catalog_signals, sync_catalog_documents
from apps.finance.models import FeeStatus, FeeStructure
from apps.finance.services import create_fee_status, create_fee_structure, record_payment


class Command(BaseCommand):
    help = (
        "Seed a realistic department, programs, courses, subjects, and one "
        "enrolled student with attendance. Safe to re-run. Catalog signals "
        "are suppressed during the seed so it doesn't fire one embedding call "
        "per row - the whole batch is synced in one pass at the end instead."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        with suppress_catalog_signals():
            self._seed()
        result = sync_catalog_documents()
        self.stdout.write(self.style.SUCCESS("Seeded academics data."))
        self.stdout.write(
            self.style.SUCCESS(
                f"Synced {result.synced} catalog document(s) ({result.removed} removed)."
            )
        )

    def _seed(self):
        department, _ = Department.objects.get_or_create(
            code="CS", defaults={"name": "Computer Science Department"}
        )

        bscs, _ = Program.objects.get_or_create(
            code="BSCS", defaults={"name": "BS Computer Science", "department": department}
        )
        bsse, _ = Program.objects.get_or_create(
            code="BSSE", defaults={"name": "BS Software Engineering", "department": department}
        )

        course_defs = [
            ("CS101", "Introduction to Programming"),
            ("MATH101", "Calculus I"),
            ("CS201", "Data Structures"),
            ("CS301", "Database Systems"),
            ("SE201", "Software Engineering Principles"),
        ]
        courses = {}
        for code, title in course_defs:
            course, _ = Course.objects.get_or_create(
                code=code, defaults={"title": title, "department": department}
            )
            courses[code] = course

        # (program, course_code, semester, credit_hours)
        subject_defs = [
            (bscs, "CS101", 1, 3),
            (bscs, "MATH101", 1, 3),
            (bscs, "CS201", 2, 4),
            (bscs, "CS301", 3, 3),
            (bsse, "CS101", 1, 4),
            (bsse, "MATH101", 1, 3),
            (bsse, "SE201", 2, 3),
        ]
        subjects = {}
        for program, course_code, semester, credit_hours in subject_defs:
            subject, _ = Subject.objects.get_or_create(
                program=program,
                course=courses[course_code],
                semester=semester,
                defaults={"credit_hours": credit_hours},
            )
            subjects[(program.code, course_code)] = subject

        user = User.objects.filter(username="ali.raza").first()
        if user is None:
            user = register_student(
                username="ali.raza",
                email="ali.raza@example.edu",
                password="Passw0rd!23",
                first_name="Ali",
                last_name="Raza",
                registration_no="BSCS-2026-001",
                program=bscs,
            )
        student = StudentProfile.objects.get(user=user)

        enrollments = []
        for course_code in ("CS101", "MATH101"):
            subject = subjects[(bscs.code, course_code)]
            try:
                enrollment = enroll_student(student=student, subject=subject)
            except ValidationError:
                enrollment = Enrollment.objects.get(student=student, subject=subject)
            enrollments.append(enrollment)

        cs101_enrollment = enrollments[0]
        attendance_history = [
            (datetime.date(2026, 7, 1), Attendance.Status.PRESENT),
            (datetime.date(2026, 7, 2), Attendance.Status.PRESENT),
            (datetime.date(2026, 7, 3), Attendance.Status.ABSENT),
            (datetime.date(2026, 7, 4), Attendance.Status.PRESENT),
            (datetime.date(2026, 7, 5), Attendance.Status.LEAVE),
        ]
        for date, status in attendance_history:
            record_attendance(enrollment=cs101_enrollment, date=date, status=status)

        bscs_structure, _ = FeeStructure.objects.get_or_create(
            program=bscs,
            semester=1,
            defaults={
                "amount": 85000,
                "breakdown": {"tuition": 70000, "lab": 10000, "library": 5000},
            },
        )
        FeeStructure.objects.get_or_create(
            program=bscs,
            semester=2,
            defaults={
                "amount": 85000,
                "breakdown": {"tuition": 70000, "lab": 10000, "library": 5000},
            },
        )

        semester_1_fee = FeeStatus.objects.filter(student=student, semester=1).first()
        if semester_1_fee is None:
            semester_1_fee = create_fee_status(
                student=student, semester=1, amount_due=bscs_structure.amount
            )
            record_payment(fee_status=semester_1_fee, amount=50000)

        FeeStatus.objects.get_or_create(
            student=student,
            semester=2,
            defaults={"amount_due": 85000},
        )
