import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'genesis_design.settings')

app = Celery('genesis_design')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
