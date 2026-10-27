from apps.academics import selectors as academics_selectors
from apps.accounts.models import User
from apps.accounts.selectors import list_users
from apps.assistant.models import Document
from apps.assistant.selectors import list_documents
from apps.content.selectors import list_announcements, list_contact_messages
from apps.finance.selectors import is_fee_status_settled, list_fee_statuses


def dashboard_callback(request, context):
    documents = list_documents()

    context["stat_cards"] = [
        {
            "label": "Students",
            "value": list_users().filter(role=User.Role.STUDENT).count(),
        },
        {
            "label": "Programs",
            "value": academics_selectors.list_programs().count(),
        },
        {
            "label": "Documents needing attention",
            "value": documents.filter(
                status__in=[Document.Status.PENDING, Document.Status.PROCESSING, Document.Status.FAILED]
            ).count(),
        },
        {
            "label": "Unpaid fee statuses",
            "value": sum(1 for fee_status in list_fee_statuses() if not is_fee_status_settled(fee_status)),
        },
    ]
    context["recent_announcements"] = list_announcements().order_by("-publish_at")[:5]
    context["recent_contact_messages"] = list_contact_messages().order_by("-created_at")[:5]
    context["documents_needing_attention"] = documents.filter(
        status__in=[Document.Status.PENDING, Document.Status.PROCESSING, Document.Status.FAILED]
    ).order_by("-updated_at")[:5]
    return context
