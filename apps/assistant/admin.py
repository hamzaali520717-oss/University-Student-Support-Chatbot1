from django.contrib import admin, messages
from django.utils.html import format_html
from unfold.admin import ModelAdmin

from apps.assistant import services
from apps.assistant.models import Document

_STATUS_COLORS = {
    Document.Status.PENDING: "#9ca3af",
    Document.Status.PROCESSING: "#2563eb",
    Document.Status.READY: "#16a34a",
    Document.Status.FAILED: "#dc2626",
}

_ALWAYS_READONLY = [
    "status",
    "error",
    "content_hash",
    "source_url",
    "source_content_type",
    "source_object_id",
    "created_at",
    "updated_at",
]


class SourceFilter(admin.SimpleListFilter):
    title = "source"
    parameter_name = "source"

    def lookups(self, request, model_admin):
        return [("uploaded", "Uploaded"), ("catalog", "Catalog-synced")]

    def queryset(self, request, queryset):
        if self.value() == "uploaded":
            return queryset.filter(source_content_type__isnull=True)
        if self.value() == "catalog":
            return queryset.filter(source_content_type__isnull=False)
        return queryset


@admin.register(Document)
class DocumentAdmin(ModelAdmin):
    list_display = [
        "title",
        "status_badge",
        "visibility",
        "source_label",
        "chunk_count",
        "updated_at",
    ]
    list_filter = ["status", "visibility", SourceFilter]
    search_fields = ["title"]
    ordering = ["-updated_at"]
    actions = ["reindex_selected"]

    @admin.display(description="Status")
    def status_badge(self, obj):
        color = _STATUS_COLORS.get(obj.status, "#9ca3af")
        tooltip = obj.error if obj.status == Document.Status.FAILED else ""
        return format_html(
            '<span title="{}" style="color:{};font-weight:600;">{}</span>',
            tooltip,
            color,
            obj.get_status_display(),
        )

    @admin.display(description="Source")
    def source_label(self, obj):
        if obj.source_content_type_id:
            return f"Synced: {obj.source_content_type.name}"
        return "Uploaded"

    @admin.display(description="Chunks")
    def chunk_count(self, obj):
        return obj.chunks.count()

    def _is_catalog_synced(self, obj):
        return bool(obj and obj.source_content_type_id)

    def get_readonly_fields(self, request, obj=None):
        if self._is_catalog_synced(obj):
            return _ALWAYS_READONLY + ["title", "file", "visibility"]
        return _ALWAYS_READONLY

    def has_delete_permission(self, request, obj=None):
        if self._is_catalog_synced(obj):
            return False
        return super().has_delete_permission(request, obj)

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        if self._is_catalog_synced(obj):
            messages.info(
                request,
                "Synced from a catalog record — edit the source (Program, Fee Structure, "
                "Admission Deadline, or Scholarship) instead; this document is overwritten "
                "automatically on the next sync.",
            )
        return super().render_change_form(
            request, context, add=add, change=change, form_url=form_url, obj=obj
        )

    def save_model(self, request, obj, form, change):
        if not change:
            document = services.create_document(
                title=obj.title, file=obj.file, visibility=obj.visibility
            )
            obj.pk = document.pk
            return
        super().save_model(request, obj, form, change)
        if "file" in form.changed_data or "visibility" in form.changed_data:
            services.reindex_document(document=obj)

    def delete_model(self, request, obj):
        services.delete_document(document=obj)

    def delete_queryset(self, request, queryset):
        for document in queryset:
            services.delete_document(document=document)

    @admin.action(description="Reindex selected uploaded documents")
    def reindex_selected(self, request, queryset):
        uploaded = list(queryset.filter(source_content_type__isnull=True))
        skipped = queryset.filter(source_content_type__isnull=False).count()
        for document in uploaded:
            services.reindex_document(document=document)
        if uploaded:
            self.message_user(request, f"Queued {len(uploaded)} document(s) for reindexing.")
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} catalog-synced document(s) — they resync automatically.",
                level=messages.WARNING,
            )
