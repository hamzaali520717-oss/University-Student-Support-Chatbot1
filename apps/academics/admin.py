from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.academics.models import (
    Attendance,
    Course,
    Department,
    Enrollment,
    Program,
    SemesterPlan,
    Subject,
)


@admin.register(Department)
class DepartmentAdmin(ModelAdmin):
    list_display = ["code", "name"]
    search_fields = ["code", "name"]
    ordering = ["code"]


@admin.register(Program)
class ProgramAdmin(ModelAdmin):
    list_display = ["code", "name", "department"]
    list_filter = ["department"]
    search_fields = ["code", "name"]
    autocomplete_fields = ["department"]
    ordering = ["code"]


@admin.register(Course)
class CourseAdmin(ModelAdmin):
    list_display = ["code", "title", "department"]
    list_filter = ["department"]
    search_fields = ["code", "title"]
    autocomplete_fields = ["department"]
    ordering = ["code"]


@admin.register(Subject)
class SubjectAdmin(ModelAdmin):
    list_display = ["course", "program", "semester", "credit_hours"]
    list_filter = ["semester", "program"]
    search_fields = ["course__code", "course__title"]
    autocomplete_fields = ["program", "course"]
    ordering = ["program", "semester"]


@admin.register(Enrollment)
class EnrollmentAdmin(ModelAdmin):
    list_display = ["student", "subject"]
    list_filter = ["subject__semester"]
    search_fields = ["student__registration_no", "subject__course__code"]
    autocomplete_fields = ["student", "subject"]


@admin.register(SemesterPlan)
class SemesterPlanAdmin(ModelAdmin):
    list_display = ["student", "semester"]
    list_filter = ["semester"]
    search_fields = ["student__registration_no"]
    autocomplete_fields = ["student"]
    filter_horizontal = ["subjects"]


@admin.register(Attendance)
class AttendanceAdmin(ModelAdmin):
    list_display = ["enrollment", "date", "status"]
    list_filter = ["status"]
    search_fields = ["enrollment__student__registration_no", "enrollment__subject__course__code"]
    autocomplete_fields = ["enrollment"]
    date_hierarchy = "date"
    ordering = ["-date"]
