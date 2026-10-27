import datetime

from django.test import TestCase
from django.utils import timezone

from apps.academics.models import Attendance, Course, Department, Program, Subject
from apps.accounts.models import StudentProfile, User

STUDENT_PASSWORD = "pw"
ADMIN_PASSWORD = "pw"


class PortalTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.department = Department.objects.create(
            code="CS-DEPT", name="Computer Science Department"
        )
        self.program = Program.objects.create(
            department=self.department, code="CS", name="Computer Science"
        )
        self.course = Course.objects.create(
            department=self.department, code="CS101", title="Intro to CS"
        )
        self.subject = Subject.objects.create(
            program=self.program, course=self.course, semester=1, credit_hours=3
        )

        self.student_user = User.objects.create_user(
            username="student1", password=STUDENT_PASSWORD, role=User.Role.STUDENT
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user, registration_no="REG-1", program=self.program
        )
        self.admin_user = User.objects.create_user(
            username="admin1", password=ADMIN_PASSWORD, role=User.Role.ADMIN
        )

    def login_student(self) -> None:
        self.client.login(username="student1", password=STUDENT_PASSWORD)

    def login_admin(self) -> None:
        self.client.login(username="admin1", password=ADMIN_PASSWORD)

    def login_profileless_student(self) -> None:
        """Logs in as a User with role=STUDENT (the model's own default,
        e.g. what `createsuperuser` produces) but no StudentProfile row -
        the case student_required must reject with 403, not crash on."""
        User.objects.create_user(
            username="profileless", password=STUDENT_PASSWORD, role=User.Role.STUDENT
        )
        self.client.login(username="profileless", password=STUDENT_PASSWORD)

    def make_subject(self, *, code: str, semester: int = 1, credit_hours: int = 3) -> Subject:
        course = Course.objects.create(
            department=self.department, code=code, title=f"{code} course"
        )
        return Subject.objects.create(
            program=self.program, course=course, semester=semester, credit_hours=credit_hours
        )

    def seed_attendance(self, enrollment, *, present_count: int, total_count: int) -> None:
        base_date = timezone.localdate()
        records = [
            Attendance(
                enrollment=enrollment,
                date=base_date - datetime.timedelta(days=i),
                status=(
                    Attendance.Status.PRESENT if i < present_count else Attendance.Status.ABSENT
                ),
            )
            for i in range(total_count)
        ]
        Attendance.objects.bulk_create(records)
