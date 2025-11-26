#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

import datetime
import json
import logging
import os

from django.core.management.base import BaseCommand

from search import solrapi
from search.management.commands.post_dirty_sounds_to_search_engine import (
    send_sounds_to_search_engine,
    update_similarity_vectors_in_search_engine,
)
from sounds.models import Sound
from utils.search import get_search_engine

console_logger = logging.getLogger("console")


class Command(BaseCommand):
    help = (
        "Take all sounds moderated and processed as OK and index them in the search engine. If there are remaining "
        "sounds in the search engine which are not in the DB, delete them as well."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "-s", "--slize_size", dest="size_size", default=5000, type=int, help="How many sounds to add at once"
        )
        parser.add_argument(
            "--immediately-create-alias",
            action="store_true",
            dest="immediately_create_alias",
            default=False,
            help="Immediately create the alias for the new index before indexing",
        )

        group = parser.add_mutually_exclusive_group(required=False)
        group.add_argument(
            "--include-similarity-vectors",
            action="store_true",
            dest="include_similarity_vectors",
            default=False,
            help="Include similarity vectors when building initial index",
        )
        group.add_argument(
            "--only-similarity-vectors",
            action="store_true",
            dest="only_similarity_vectors",
            default=False,
            help="Add similarity vectors to sounds that already exist in the index",
        )

    def handle(self, *args, **options):
        search_engine = get_search_engine()
        include_similarity_vectors = options["include_similarity_vectors"]
        only_similarity_vectors = options["only_similarity_vectors"]

        schema_directory = os.path.join(".", "utils", "search", "schema")
        freesound_schema_definition = json.load(open(os.path.join(schema_directory, "freesound.json")))
        delete_default_fields_definition = json.load(open(os.path.join(schema_directory, "delete_default_fields.json")))
        current_date = datetime.datetime.now().strftime("%Y%m%d-%H%M")

        # If we update existing documents, we send to the freesound collection alias, otherwise we create a new collection
        if only_similarity_vectors:
            collection_name = "freesound"
        else:
            collection_name = f"freesound_{current_date}"
        collection_url = f"{search_engine.solr_base_url}/solr/{collection_name}"
        solr_api = solrapi.SolrManagementAPI(search_engine.solr_base_url, collection_name)
        if not only_similarity_vectors:
            solr_api.create_collection_and_schema(
                delete_default_fields_definition, freesound_schema_definition, "username"
            )

        if options["immediately_create_alias"]:
            console_logger.info("Creating the freesound alias to point to the new index")
            solr_api.create_collection_alias("freesound")

        # Get all sounds moderated and processed ok and add them to the search engine
        # Don't delete existing sounds in each loop because we clean up in the final step
        sounds_to_index_ids = list(
            Sound.objects.filter(processing_state="OK", moderation_state="OK").values_list("id", flat=True)
        )

        if only_similarity_vectors:
            console_logger.info(
                "Updating similarity vectors for %d sounds in the search engine", len(sounds_to_index_ids)
            )
            update_similarity_vectors_in_search_engine(
                sounds_to_index_ids, slice_size=options["size_size"], solr_collection_url=collection_url
            )
        else:
            console_logger.info("Indexing %d sounds to the search engine", len(sounds_to_index_ids))
            send_sounds_to_search_engine(
                sounds_to_index_ids,
                slice_size=options["size_size"],
                solr_collection_url=collection_url,
                include_similarity_vectors=include_similarity_vectors,
            )

        if not only_similarity_vectors:
            console_logger.info("Updating the freesound alias to point to the new index")
            solr_api.create_collection_alias("freesound")
