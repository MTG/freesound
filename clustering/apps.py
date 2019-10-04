from django.conf import settings
from django.apps import AppConfig
from . import init_clustering_engine


class ClusteringConfig(AppConfig):
    name = 'clustering'
    
    def ready(self):
        if settings.IS_CELERY_WORKER:
            init_clustering_engine()
