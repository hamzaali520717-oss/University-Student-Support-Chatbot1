from django.urls import reverse

from apps.academics.models import Course, Department, Enrollment, Program, Subject
from apps.accounts.models import StudentProfile, User
from apps.portal.tests.base import PortalTestCase


class EnrollmentsViewTests(PortalTestCase):
    def _make_other_program_subject(self):
        department = Department.objects.create(
            code="EE-DEPT", name="Electrical Engineering Department"
        )
        program = Program.objects.create(department=department, code="EE", name="Electrical Engineering")
        course = Course.objects.create(department=department, code="EE101", title="Circuits")
        return Subject.objects.create(program=program, course=course, semester=1, credit_hours=3)

    def test_lists_only_own_enrollments(self):
        # CS999 is in the same program as the logged-in student, so it's
        # expected to appear in their own "available subjects" browse list -
        # what must NOT happen is it showing up in their *enrollments* list,
        # since it's a different student's enrollment.
        other_user = User.objects.create_user(username="student2", password="pw", role=User.Role.STUDENT)
        other_student = StudentProfile.objects.create(
            user=other_user, registration_no="REG-2", program=self.program
        )
        other_subject = self.make_subject(code="CS999")

        Enrollment.objects.create(student=self.student, subject=self.subject)
        Enrollment.objects.create(student=other_student, subject=other_subject)

        self.login_student()
        response = self.client.get(reverse("portal:enrollments"))
        enrolled_codes = {
            enrollment.subject.course.code for enrollment in response.context["enrollments"]
        }
        self.assertEqual(enrolled_codes, {"CS101"})

    def test_browse_list_scoped_to_own_program_and_excludes_enrolled(self):
        other_subject = self._make_other_program_subject()
        second_own_subject = self.make_subject(code="CS102")

        self.login_student()
        response = self.client.get(reverse("portal:enrollments"))
        codes = {subject.course.code for subject in response.context["available_subjects"]}
        self.assertIn("CS101", codes)
        self.assertIn("CS102", codes)
        self.assertNotIn("EE101", codes)

        Enrollment.objects.create(student=self.student, subject=self.subject)
        response = self.client.get(reverse("portal:enrollments"))
        codes = {subject.course.code for subject in response.context["available_subjects"]}
        self.assertNotIn("CS101", codes)
        self.assertIn("CS102", codes)

    def test_post_enroll_success_redirects_and_creates_row(self):
        self.login_student()
        response = self.client.post(reverse("portal:enrollments"), {"subject": self.subject.id})
        self.assertRedirects(response, reverse("portal:enrollments"))
        self.assertTrue(Enrollment.objects.filter(student=self.student, subject=self.subject).exists())

    def test_post_enroll_duplicate_shows_message_and_no_second_row(self):
        Enrollment.objects.create(student=self.student, subject=self.subject)
        self.login_student()
        response = self.client.post(
            reverse("portal:enrollments"), {"subject": self.subject.id}, follow=True
        )
        page_messages = list(response.context["messages"])
        self.assertTrue(any("Already enrolled" in str(m) for m in page_messages))
        self.assertEqual(
            Enrollment.objects.filter(student=self.student, subject=self.subject).count(), 1
        )

    def test_post_enroll_different_program_subject_404s(self):
        other_subject = self._make_other_program_subject()
        self.login_student()
        response = self.client.post(reverse("portal:enrollments"), {"subject": other_subject.id})
        self.assertEqual(response.status_code, 404)

    def test_enroll_buttons_have_distinguishing_accessible_names(self):
        # Every "Enroll" button previously shared the identical accessible
        # name "Enroll" - a screen-reader user tabbing through the buttons
        # list couldn't tell which subject each one enrolled in.
        self.make_subject(code="CS102")
        self.login_student()
        response = self.client.get(reverse("portal:enrollments"))
        self.assertContains(response, 'aria-label="Enroll in CS101 Intro to CS"')
        self.assertContains(response, 'aria-label="Enroll in CS102 CS102 course"')
