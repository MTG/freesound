from __future__ import absolute_import
import os
import requests
from django.conf import settings

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'freesound.settings')

app = Celery('freesound')

# Using a string here means the worker don't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load tasks from only the clustering app.
app.autodiscover_tasks()
# Maybe app.autodiscover_tasks( settings.INSTALLED_APPS) is needed?


def get_queues_task_counts():
    try:
        raw_data = requests.get('http://{}:{}/api/queues'.format(settings.RABBITMQ_HOST, settings.RABBITMQ_API_PORT),
                                auth=(settings.RABBITMQ_USER, settings.RABBITMQ_PASS)).json()
    except Exception as e:
        raw_data = []
        print e

    data = []
    for queue_data in raw_data:
        queue_name = queue_data['name']
        if 'celery' in queue_name:
            continue
        try:
            message_rate = queue_data['message_stats']['ack_details']['rate']
        except KeyError:
            message_rate = -1
        data.append((queue_name,
                     queue_data['messages_ready'],
                     queue_data['messages_unacknowledged'],
                     queue_data['consumers'],
                     message_rate
                     ))

    data = sorted(data, key=lambda x: x[0])
    return data
