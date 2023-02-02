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

import logging

from django.core.management.base import BaseCommand

from forum.models import Post
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

        parser.add_argument(
            '-c', '--clear_index',
            action='store_true',
            dest='clear_index',
            default=False,
            help='Clear all posts in the existing index before re-indexing all posts. This option is normally not '
                 'needed as the command will clean any leftover posts from the search index which are no longer'
                 'in the DB.')

    def handle(self, *args, **options):
        # If indicated, first remove all documents in the index
        clear_index = options['clear_index']
        if clear_index:
            delete_all_posts_from_search_engine()

        # Select all moderated forum posts and index them
        all_posts = Post.objects.select_related("thread", "author", "thread__author", "thread__forum")\
            .filter(moderation_state="OK")
        num_posts = len(all_posts)
        console_logger.info("Re-indexing %d forum posts", num_posts)
        slice_size = options['size_size']
        for i in range(0, num_posts, slice_size):
            post_ids_slice = all_posts[i:i + slice_size]
            add_posts_to_search_engine(post_ids_slice)

        # Find all indexed forum posts which are not in the DB and remove them. This part of the code should do nothing
        # as deleted forum posts should be removed from the index in due time. In particular, if the "clear index" is
        # passed, this bit of code should remove no posts.
        indexed_post_ids = get_all_post_ids_from_search_engine()
        post_ids_to_delete = list(set(indexed_post_ids).difference(all_posts.values_list('id', flat=True)))
        console_logger.info("Deleting %d non-existing posts form the search engine", len(post_ids_to_delete))
        if post_ids_to_delete:
            delete_posts_from_search_engine(post_ids_to_delete)
