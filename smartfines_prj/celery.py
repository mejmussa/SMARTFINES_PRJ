import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartfines_prj.settings')

app = Celery('smartfines_prj')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()