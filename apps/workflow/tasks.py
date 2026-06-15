from celery import shared_task
from django.utils import timezone

from apps.designs.models import DesignRequest, DesignStatus, DeadlineStatus
from apps.workflow.deadline_utils import compute_target_escalation_level, get_deadline_config
from apps.workflow.services import update_deadline_status


def check_deadline_statuses():
    """Update Green/Yellow/Red for all active designs with a deadline."""
    active_statuses = [
        s for s in DesignStatus.values
        if s not in [DesignStatus.COMPLETED, DesignStatus.CANCELLED, DesignStatus.DRAFT]
    ]
    designs = DesignRequest.objects.filter(
        status__in=active_statuses,
        deadline_due__isnull=False,
    )
    for design in designs:
        update_deadline_status(design)
    return designs.count()


def process_deadline_escalations():
    """Send escalation notifications based on Deadline Configuration delays."""
    from apps.notifications.services import send_escalation
    from apps.designs.models import DeadlineRecord

    config = get_deadline_config()
    if not config.auto_breach_notify:
        return 0

    now = timezone.now()
    breached = DeadlineRecord.objects.filter(
        status=DeadlineStatus.RED,
        breached_at__isnull=False,
        escalation_level__lt=4,
    ).select_related('design')

    processed = 0
    for record in breached:
        target_level = compute_target_escalation_level(record.breached_at, now=now, config=config)
        if target_level <= record.escalation_level:
            continue
        for level in range(record.escalation_level + 1, target_level + 1):
            send_escalation(record.design, level)
        record.escalation_level = target_level
        record.save(update_fields=['escalation_level'])
        processed += 1
    return processed


@shared_task(name='apps.workflow.tasks.check_deadline_statuses')
def check_deadline_statuses_task():
    return check_deadline_statuses()


@shared_task(name='apps.workflow.tasks.process_deadline_escalations')
def process_deadline_escalations_task():
    return process_deadline_escalations()
