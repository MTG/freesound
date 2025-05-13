import json
import os
from urllib.parse import urljoin

from django.conf import settings
from django.core.management.base import BaseCommand

from search import solrapi

class Command(BaseCommand):

    help = "Create a schema in a solr core"

    def handle(self, *args, **options):
        schema_directory = os.path.join('.', "utils", "search", "schema")
        freesound_schema_definition = json.load(open(os.path.join(schema_directory, "freesound.json")))
        forum_schema_definition = json.load(open(os.path.join(schema_directory, "forum.json")))
        solr_base_url = "http://search:8983"
        solrapi.create_collection_and_schema("freesound", freesound_schema_definition, "username", solr_base_url)
        solrapi.create_collection_and_schema("forum", forum_schema_definition, "thread_id", solr_base_url)
