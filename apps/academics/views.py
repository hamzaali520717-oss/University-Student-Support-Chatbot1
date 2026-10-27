from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from apps.academics import selectors, services
from apps.academics.serializers import (
    AttendanceSerializer,
    CourseSerializer,
    EnrollmentCreateSerializer,
    EnrollmentSerializer,
    ProgramSerializer,
    SemesterPlanSerializer,
    SubjectSerializer,
)
from apps.core.permissions import IsStudent


class ProgramListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProgramSerializer
    queryset = selectors.list_programs()


class CourseListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = CourseSerializer
    queryset = selectors.list_courses()


class SubjectListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = SubjectSerializer

    def get_queryset(self):
        return selectors.list_subjects(program_code=self.request.query_params.get("program"))


class MyEnrollmentListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsStudent]
    serializer_class = EnrollmentSerializer

    def get_queryset(self):
        return selectors.list_student_enrollments(student=self.request.user.student_profile)

    def post(self, request: Request) -> Response:
        serializer = EnrollmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            enrollment = services.enroll_student(
                student=request.user.student_profile,
                subject=serializer.validated_data["subject"],
            )
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.messages)
        return Response(
            EnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED
        )


class MyAttendanceListView(generics.ListAPIView):
    permission_classes = [IsStudent]
    serializer_class = AttendanceSerializer

    def get_queryset(self):
        return selectors.list_student_attendance(
            student=self.request.user.student_profile,
            subject_id=self.request.query_params.get("subject"),
        )


class MySemesterPlanListView(generics.ListAPIView):
    permission_classes = [IsStudent]
    serializer_class = SemesterPlanSerializer

    def get_queryset(self):
        return selectors.list_student_semester_plans(student=self.request.user.student_profile)
