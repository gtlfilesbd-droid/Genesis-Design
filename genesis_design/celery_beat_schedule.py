from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'check-deadline-statuses': {
        'task': 'apps.workflow.tasks.check_deadline_statuses_task',
        'schedule': crontab(minute='*/30'),
    },
    'process-deadline-escalations': {
        'task': 'apps.workflow.tasks.process_deadline_escalations_task',
        'schedule': crontab(minute='0', hour='*/1'),
    },
    'check-action-sla-breaches': {
        'task': 'apps.workflow.tasks.check_action_sla_breaches_task',
        'schedule': crontab(minute='*/15'),
    },
}
