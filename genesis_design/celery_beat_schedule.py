from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'check-sla-statuses': {
        'task': 'apps.workflow.tasks.check_sla_statuses',
        'schedule': crontab(minute='*/30'),
    },
    'process-sla-escalations': {
        'task': 'apps.workflow.tasks.process_sla_escalations',
        'schedule': crontab(minute='0', hour='*/1'),
    },
}
