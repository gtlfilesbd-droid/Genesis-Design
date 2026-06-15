from django.apps import AppConfig


class WorkflowConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.workflow'
    label = 'workflow'

    def ready(self):
        if not self._should_start_scheduler():
            return
        from apps.workflow.scheduler import start_background_scheduler

        start_background_scheduler()
        print(
            'Genesis Design: deadline auto-check enabled '
            '(status every 30 min, escalation every 60 min — no Celery/Docker needed)'
        )

    @staticmethod
    def _should_start_scheduler():
        import os
        import sys

        from django.conf import settings

        if not getattr(settings, 'DEADLINE_AUTO_SCHEDULER', True):
            return False
        if 'test' in sys.argv or 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            return False
        if 'runserver' not in sys.argv:
            return False
        if os.environ.get('RUN_MAIN') == 'true':
            return True
        return '--noreload' in sys.argv
