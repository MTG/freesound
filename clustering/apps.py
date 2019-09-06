from django.conf import settings
from django.apps import AppConfig
from . import init_clustering_engine


class ClusteringConfig(AppConfig):
    name = 'clustering'
    
    def ready(self):
        if settings.ENV_CELERY_WORKER == '1':  # only in celery workers
            init_clustering_engine()
