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
import time

from django.core.management.base import BaseCommand

from forum.models import Post
from search import solrapi
from search.management.commands.post_dirty_sounds_to_search_engine import time_stats
from utils.search import get_search_engine
from utils.search.search_forum import add_posts_to_search_engine, get_all_post_ids_from_search_engine, \
    delete_all_posts_from_search_engine, delete_posts_from_search_engine

console_logger = logging.getLogger("console")


class Command(BaseCommand):
    help = 'Index all moderated forum posts in the search engine. If there are remaining forum posts in the search' \
           'engine which are not in the DB, delete them as well.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-s', '--slize_size',
            dest='size_size',
            default=4000,
            type=int,
            help='How many posts to add at once')

    def handle(self, *args, **options):
        search_engine = get_search_engine()

        schema_directory = os.path.join('.', "utils", "search", "schema")
        forum_schema_definition = json.load(open(os.path.join(schema_directory, "forum.json")))
        delete_default_fields_definition = json.load(open(os.path.join(schema_directory, "delete_default_fields.json")))

        current_date = datetime.datetime.now().strftime("%Y%m%d-%H%M")

        collection_name = f"forum_{current_date}"
        new_collection_url = f"{search_engine.solr_base_url}/solr/{collection_name}"
        solr_api = solrapi.SolrManagementAPI(search_engine.solr_base_url, collection_name)
        solr_api.create_collection_and_schema(delete_default_fields_definition, forum_schema_definition, "thread_id")

        # Select all moderated forum posts and index them
        all_posts = Post.objects.select_related("thread", "author", "thread__author", "thread__forum")\
            .filter(moderation_state="OK")
        num_posts = len(all_posts)
        console_logger.info("Re-indexing %d forum posts", num_posts)
        slice_size = options['size_size']
        n_posts_indexed_correctly = 0
        starttime = time.monotonic()
        for i in range(0, num_posts, slice_size):
            post_ids_slice = all_posts[i:i + slice_size]
            n_posts_indexed = len(post_ids_slice)
            add_posts_to_search_engine(post_ids_slice, solr_collection_url=new_collection_url)
            n_posts_indexed_correctly += n_posts_indexed
            elapsed, remaining = time_stats(n_posts_indexed_correctly, num_posts, starttime)
            console_logger.info(f"Added {n_posts_indexed_correctly}/{num_posts} posts. Elapsed: {elapsed}, Remaining: {remaining}")

        console_logger.info("Updating the forum alias to point to the new index")
        solr_api.create_collection_alias("forum")
