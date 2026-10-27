from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.admissions.models import AdmissionDeadline, AdmissionRequirement, Scholarship


@admin.register(AdmissionRequirement)
class AdmissionRequirementAdmin(ModelAdmin):
    list_display = ["program", "title"]
    list_filter = ["program"]
    search_fields = ["title", "program__code", "program__name"]
    autocomplete_fields = ["program"]


@admin.register(AdmissionDeadline)
class AdmissionDeadlineAdmin(ModelAdmin):
    list_display = ["program", "label", "date"]
    list_filter = ["program"]
    search_fields = ["label", "program__code", "program__name"]
    autocomplete_fields = ["program"]
    date_hierarchy = "date"
    ordering = ["date"]


@admin.register(Scholarship)
class ScholarshipAdmin(ModelAdmin):
    list_display = ["name", "amount", "is_active"]
    list_editable = ["is_active"]
    list_filter = ["is_active"]
    search_fields = ["name"]
    ordering = ["name"]
