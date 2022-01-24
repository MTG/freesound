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

from django.conf import settings

import forum.models
from utils.text import remove_control_chars
from utils.search import get_search_engine_forum, SearchEngineException

search_logger = logging.getLogger("search")
console_logger = logging.getLogger("console")


def add_posts_to_search_engine_by_id(post_ids):
    """Add forum posts to search engine
    Arguments:
        post_ids (List[int]): IDs of the post objects to add"""

    posts = forum.models.Post.objects.select_related("thread", "author", "thread__author", "thread__forum").filter(id__in=post_ids)
    num_posts = posts.count()
    try:
        console_logger.info("Adding %d posts to solr index" % num_posts)
        search_logger.info("Adding %d posts to solr index" % num_posts)
        get_search_engine_forum().add_forum_posts_to_index(posts)
    except SearchEngineException as e:
        search_logger.error("Failed to add posts to search engine index, reason: %s" % str(e))
    
    
def add_all_posts_to_search_engine(slice_size=4000):
    """Add all forum posts to the search engine
    Arguments:
        slice_size (int): The number of posts to send to the search engine at a time"""

    posts = forum.models.Post.objects.select_related("thread", "author", "thread__author", "thread__forum").all()

    num_posts = posts.count()
    for i in range(0, num_posts, slice_size):
        posts_slice = posts[i:i+slice_size]
        num_posts = len(posts_slice)
        try:
            console_logger.info("Adding %d posts to solr index" % num_posts)
            search_logger.info("Adding %d posts to solr index" % num_posts)
            get_search_engine_forum().add_forum_posts_to_index(posts_slice)
        except SearchEngineException as e:
            search_logger.error("Failed to add posts to search engine index, reason: %s" % str(e))


def delete_post_from_search_engine(post_id):
    search_logger.info("deleting post with id %d" % post_id)
    try:
        get_search_engine_forum().remove_from_index(post_id)
    except SearchEngineException as e:
        search_logger.error('Could not delete post with id %s (%s).' % (post_id, e))
