from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'check-deadline-statuses': {
        'task': 'apps.workflow.tasks.check_deadline_statuses',
        'schedule': crontab(minute='*/30'),
    },
    'process-deadline-escalations': {
        'task': 'apps.workflow.tasks.process_deadline_escalations',
        'schedule': crontab(minute='0', hour='*/1'),
    },
}
