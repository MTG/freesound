from django_extensions.management.jobs import BaseJob

from utils.search.search import add_all_sounds_to_solr

class Job(BaseJob):
    help = "Updates all sounds in search index"

    def execute(self):
        # executing empty sample job
        add_all_sounds_to_solr()
