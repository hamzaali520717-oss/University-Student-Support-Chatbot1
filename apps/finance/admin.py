from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.finance.models import FeeStatus, FeeStructure


@admin.register(FeeStructure)
class FeeStructureAdmin(ModelAdmin):
    list_display = ["program", "semester", "amount"]
    list_filter = ["program", "semester"]
    search_fields = ["program__code", "program__name"]
    autocomplete_fields = ["program"]
    ordering = ["program", "semester"]


@admin.register(FeeStatus)
class FeeStatusAdmin(ModelAdmin):
    list_display = ["student", "semester", "amount_due", "amount_paid", "status"]
    list_filter = ["status", "semester"]
    search_fields = ["student__registration_no", "student__user__username"]
    autocomplete_fields = ["student"]
    ordering = ["student", "semester"]
