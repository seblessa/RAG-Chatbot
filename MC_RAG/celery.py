import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MC_RAG.settings')

app = Celery('MC_RAG',
             )
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

CELERY_ROUTES = {
    'documents.tasks.*': {'queue': 'chat_app_queue'},
    # 'documents.tasks.process_message': {'queue': 'chat_app_queue'},
}
