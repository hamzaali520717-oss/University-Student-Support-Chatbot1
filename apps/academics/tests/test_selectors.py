from django.test import TestCase

from apps.academics import selectors
from apps.academics.models import Attendance, Course, Department, Enrollment, Program, Subject
from apps.accounts.models import StudentProfile, User


class SubjectSelectorTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.cs = Program.objects.create(department=self.department, code="CS", name="Computer Science")
        self.se = Program.objects.create(department=self.department, code="SE", name="Software Engineering")
        self.course = Course.objects.create(
            department=self.department, code="CS101", title="Intro to Programming"
        )
        self.cs_subject = Subject.objects.create(
            program=self.cs, course=self.course, semester=1, credit_hours=3
        )
        self.se_subject = Subject.objects.create(
            program=self.se, course=self.course, semester=1, credit_hours=4
        )

    def test_list_subjects_unfiltered_returns_all(self):
        self.assertEqual(selectors.list_subjects().count(), 2)

    def test_list_subjects_filtered_by_program(self):
        result = selectors.list_subjects(program_code="CS")
        self.assertEqual(list(result), [self.cs_subject])


class ProgramStatsSelectorTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=self.department, code="CS", name="Computer Science"
        )
        self.empty_program = Program.objects.create(
            department=self.department, code="SE", name="Software Engineering"
        )
        self.course = Course.objects.create(
            department=self.department, code="CS101", title="Intro to Programming"
        )
        Subject.objects.create(program=self.program, course=self.course, semester=1, credit_hours=3)
        Subject.objects.create(program=self.program, course=self.course, semester=2, credit_hours=4)

    def test_annotates_subject_count_and_total_credit_hours(self):
        result = {p.code: p for p in selectors.list_programs_with_stats()}
        self.assertEqual(result["CS"].subject_count, 2)
        self.assertEqual(result["CS"].total_credit_hours, 7)

    def test_program_with_no_subjects_has_zero_count_and_null_total(self):
        result = {p.code: p for p in selectors.list_programs_with_stats()}
        self.assertEqual(result["SE"].subject_count, 0)
        self.assertIsNone(result["SE"].total_credit_hours)


class UniqueDepartmentsFromProgramsTests(TestCase):
    def test_deduplicates_and_sorts_by_code(self):
        cs_dept = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        gen_dept = Department.objects.create(code="GEN", name="General")
        cs_program = Program.objects.create(department=cs_dept, code="CS", name="Computer Science")
        se_program = Program.objects.create(department=cs_dept, code="SE", name="Software Engineering")
        gen_program = Program.objects.create(department=gen_dept, code="GEN-PRG", name="General Studies")

        result = selectors.unique_departments_from_programs(
            programs=[cs_program, se_program, gen_program]
        )

        self.assertEqual(result, [cs_dept, gen_dept])

    def test_empty_programs_returns_empty_list(self):
        self.assertEqual(selectors.unique_departments_from_programs(programs=[]), [])


class StudentScopedSelectorTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        self.program = Program.objects.create(
            department=self.department, code="CS", name="Computer Science"
        )
        self.course = Course.objects.create(
            department=self.department, code="CS101", title="Intro to Programming"
        )
        self.subject = Subject.objects.create(
            program=self.program, course=self.course, semester=1, credit_hours=3
        )

        user_a = User.objects.create_user(username="stu-a", password="pw")
        self.student_a = StudentProfile.objects.create(
            user=user_a, registration_no="REG-A", program=self.program
        )
        user_b = User.objects.create_user(username="stu-b", password="pw")
        self.student_b = StudentProfile.objects.create(
            user=user_b, registration_no="REG-B", program=self.program
        )

        self.enrollment_a = Enrollment.objects.create(student=self.student_a, subject=self.subject)
        Enrollment.objects.create(student=self.student_b, subject=self.subject)
        Attendance.objects.create(enrollment=self.enrollment_a, date="2026-07-01")

    def test_list_student_enrollments_scoped_to_student(self):
        result = selectors.list_student_enrollments(student=self.student_a)
        self.assertEqual(list(result), [self.enrollment_a])

    def test_list_student_attendance_scoped_to_student(self):
        result = selectors.list_student_attendance(student=self.student_b)
        self.assertEqual(result.count(), 0)
        result = selectors.list_student_attendance(student=self.student_a)
        self.assertEqual(result.count(), 1)

    def test_list_student_attendance_subject_zero_does_not_return_unfiltered_results(self):
        # subject_id=0 is a valid (if nonexistent) int, not "no filter" -
        # `if subject_id:` previously treated 0 as falsy and silently
        # returned the student's whole attendance history instead.
        result = selectors.list_student_attendance(student=self.student_a, subject_id=0)
        self.assertEqual(result.count(), 0)

    def test_list_student_attendance_subject_none_means_unfiltered(self):
        result = selectors.list_student_attendance(student=self.student_a, subject_id=None)
        self.assertEqual(result.count(), 1)


class SummarizeAttendanceTests(TestCase):
    def setUp(self):
        department = Department.objects.create(code="CS-DEPT", name="Computer Science Department")
        program = Program.objects.create(department=department, code="CS", name="Computer Science")
        course = Course.objects.create(department=department, code="CS101", title="Intro to CS")
        subject = Subject.objects.create(program=program, course=course, semester=1, credit_hours=3)
        user = User.objects.create_user(username="stu", password="pw")
        student = StudentProfile.objects.create(user=user, registration_no="REG-1", program=program)
        self.enrollment = Enrollment.objects.create(student=student, subject=subject)

    def test_empty_records_returns_zeroed_summary(self):
        summary = selectors.summarize_attendance([])
        self.assertEqual(summary, {"total": 0, "present": 0, "rate": 0})

    def test_rate_rounds_to_nearest_percent(self):
        records = [
            Attendance.objects.create(
                enrollment=self.enrollment, date=f"2026-07-{i:02d}", status=Attendance.Status.PRESENT
            )
            for i in range(1, 3)
        ] + [
            Attendance.objects.create(
                enrollment=self.enrollment, date="2026-07-03", status=Attendance.Status.ABSENT
            )
        ]
        summary = selectors.summarize_attendance(records)
        self.assertEqual(summary, {"total": 3, "present": 2, "rate": 67})
