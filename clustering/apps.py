from django.apps import AppConfig
from . import init_clustering_engine


class ClusteringConfig(AppConfig):
    name = 'clustering'
    
    def ready(self):
        init_clustering_engine()  # TODO: ensure that this is not ran on prod web server
