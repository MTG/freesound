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
        delete_default_fields_definition = json.load(open(os.path.join(schema_directory, "delete_default_fields.json")))
        freesound_schema_definition = json.load(open(os.path.join(schema_directory, "freesound.json")))
        forum_schema_definition = json.load(open(os.path.join(schema_directory, "forum.json")))
        solr_base_url = "http://search:8983"

        # Create freesound collection
        freesound_api = solrapi.SolrManagementAPI(solr_base_url, "freesound1234")
        freesound_api.create_collection_and_schema(delete_default_fields_definition, freesound_schema_definition, "username")
        freesound_api.create_collection_alias("freesound")

        # Create forum collection
        forum_api = solrapi.SolrManagementAPI(solr_base_url, "forum1234")
        forum_api.create_collection_and_schema(delete_default_fields_definition, forum_schema_definition, "thread_id")
        forum_api.create_collection_alias("forum")