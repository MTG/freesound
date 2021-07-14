from __future__ import absolute_import
import os
import base64
import json

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
app.autodiscover_tasks('clustering', related_name='tasks')
app.autodiscover_tasks('sounds', related_name='tasks')

# Route tasks to individual queues
app.conf.task_routes = {
    'clustering.cluster_sounds': {'queue': 'clustering'},
    'sounds.analyze_method1': {'queue': 'analyze_method1'},
    'sounds.analyze_method2': {'queue': 'analyze_method2'},
}


def get_queue_tasks_body(queue_name):

    with app.pool.acquire(block=True) as conn:
        tasks = conn.default_channel.client.lrange(queue_name, 0, -1)
        decoded_tasks = []

    for task in tasks:
        j = json.loads(task)
        body = json.loads(base64.b64decode(j['body']))
        decoded_tasks.append(body)

    return decoded_tasks


def get_queues_task_counts():
    data = []
    # TODO: get celery queue names automatically
    print(app.queues.keys())
    for queue_name in ['clustering', 'analyze_method1', 'analyze_method2']:
        data.append((queue_name, len(get_queue_tasks_body(queue_name))))
    return data

