from rest_framework import serializers

from apps.academics.models import (
    Attendance,
    Course,
    Enrollment,
    Program,
    SemesterPlan,
    Subject,
)


class ProgramSerializer(serializers.ModelSerializer):
    department = serializers.SlugRelatedField(slug_field="code", read_only=True)

    class Meta:
        model = Program
        fields = ["code", "name", "department"]


class CourseSerializer(serializers.ModelSerializer):
    department = serializers.SlugRelatedField(slug_field="code", read_only=True)

    class Meta:
        model = Course
        fields = ["code", "title", "department"]


class SubjectSerializer(serializers.ModelSerializer):
    program = serializers.SlugRelatedField(slug_field="code", read_only=True)
    course = CourseSerializer(read_only=True)

    class Meta:
        model = Subject
        fields = ["id", "program", "course", "semester", "credit_hours"]


class EnrollmentSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)

    class Meta:
        model = Enrollment
        fields = ["id", "subject", "created_at"]


class EnrollmentCreateSerializer(serializers.Serializer):
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all())


class AttendanceSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(source="enrollment.subject", read_only=True)

    class Meta:
        model = Attendance
        fields = ["id", "subject", "date", "status"]


class SemesterPlanSerializer(serializers.ModelSerializer):
    subjects = SubjectSerializer(many=True, read_only=True)

    class Meta:
        model = SemesterPlan
        fields = ["id", "semester", "subjects"]
