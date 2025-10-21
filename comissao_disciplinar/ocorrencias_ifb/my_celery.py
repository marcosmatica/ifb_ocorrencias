# ocorrencias_ifb/my_celery.py
import os
#from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ocorrencias_ifb.settings')

#app = Celery('ocorrencias_ifb')
#app.config_from_object('django.conf:settings', namespace='CELERY')
#app.autodiscover_tasks()