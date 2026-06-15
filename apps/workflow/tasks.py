from celery import shared_task
from django.utils import timezone

from apps.designs.models import DesignRequest, DesignStatus, DeadlineStatus
from apps.workflow.services import update_deadline_status


@shared_task
def check_deadline_statuses():
    active_statuses = [
        s for s in DesignStatus.values
        if s not in [DesignStatus.COMPLETED, DesignStatus.CANCELLED, DesignStatus.DRAFT]
    ]
    for design in DesignRequest.objects.filter(status__in=active_statuses, deadline_due__isnull=False):
        update_deadline_status(design)


@shared_task
def process_deadline_escalations():
    from apps.notifications.services import send_escalation
    from apps.designs.models import DeadlineRecord

    breached = DeadlineRecord.objects.filter(
        status=DeadlineStatus.RED,
        escalation_level__lt=4,
    ).select_related('design')

    for record in breached:
        record.escalation_level += 1
        record.save(update_fields=['escalation_level'])
        send_escalation(record.design, record.escalation_level)
