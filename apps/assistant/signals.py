from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.academics.models import Program, Subject
from apps.admissions.models import AdmissionDeadline, AdmissionRequirement, Scholarship
from apps.assistant.services.catalog import (
    catalog_signals_suppressed,
    delete_synced_document,
    sync_source,
)
from apps.finance.models import FeeStructure


def _schedule_sync(*, source) -> None:
    if catalog_signals_suppressed():
        return
    transaction.on_commit(lambda: sync_source(source=source))


def _schedule_delete(*, source) -> None:
    if catalog_signals_suppressed():
        return
    # Capture the key now: Django clears instance.pk right after delete()
    # returns, before this on_commit callback would run.
    content_type_id = ContentType.objects.get_for_model(type(source)).id
    object_id = source.pk
    transaction.on_commit(
        lambda: delete_synced_document(content_type_id=content_type_id, object_id=object_id)
    )


@receiver(post_save, sender=Program)
def _program_saved(sender, instance, raw, **kwargs):
    if raw:
        return
    _schedule_sync(source=instance)


@receiver(post_delete, sender=Program)
def _program_deleted(sender, instance, **kwargs):
    _schedule_delete(source=instance)


@receiver(post_save, sender=FeeStructure)
def _fee_structure_saved(sender, instance, raw, **kwargs):
    if raw:
        return
    _schedule_sync(source=instance)


@receiver(post_delete, sender=FeeStructure)
def _fee_structure_deleted(sender, instance, **kwargs):
    _schedule_delete(source=instance)


@receiver(post_save, sender=AdmissionDeadline)
def _admission_deadline_saved(sender, instance, raw, **kwargs):
    if raw:
        return
    _schedule_sync(source=instance)


@receiver(post_delete, sender=AdmissionDeadline)
def _admission_deadline_deleted(sender, instance, **kwargs):
    _schedule_delete(source=instance)


@receiver(post_save, sender=Scholarship)
def _scholarship_saved(sender, instance, raw, **kwargs):
    if raw:
        return
    _schedule_sync(source=instance)


@receiver(post_delete, sender=Scholarship)
def _scholarship_deleted(sender, instance, **kwargs):
    _schedule_delete(source=instance)


@receiver(post_save, sender=Subject)
def _subject_saved(sender, instance, raw, **kwargs):
    # Subject isn't a RenderedSource itself - it's folded into its program's
    # chunk (see render_program) - so a subject change re-syncs the owning
    # program instead of syncing the subject.
    if raw:
        return
    _schedule_sync(source=instance.program)


@receiver(post_delete, sender=Subject)
def _subject_deleted(sender, instance, **kwargs):
    _schedule_sync(source=instance.program)


@receiver(post_save, sender=AdmissionRequirement)
def _admission_requirement_saved(sender, instance, raw, **kwargs):
    # Same as Subject above: AdmissionRequirement has no chunk of its own -
    # render_program folds a program's requirements into its own chunk - so a
    # requirement change re-syncs the owning program instead of syncing the
    # requirement.
    if raw:
        return
    _schedule_sync(source=instance.program)


@receiver(post_delete, sender=AdmissionRequirement)
def _admission_requirement_deleted(sender, instance, **kwargs):
    _schedule_sync(source=instance.program)
