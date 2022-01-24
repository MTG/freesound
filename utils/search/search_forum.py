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
from utils.search.backend.pysolr.wrapper import SearchEngine, SearchEngineException

search_logger = logging.getLogger("search")


def convert_to_search_engine_document(post):
    document = {
        "id": post.id,
        "thread_id": post.thread.id,
        "thread_title": remove_control_chars(post.thread.title),
        "thread_author": post.thread.author,
        "thread_created": post.thread.created,

        "forum_name": post.thread.forum.name,
        "forum_name_slug": post.thread.forum.name_slug,

        "post_author": post.author,
        "post_created": post.created,
        "post_body": remove_control_chars(post.body),

        "num_posts": post.thread.num_posts,
        "has_posts": False if post.thread.num_posts == 0 else True
    }

    return document


def send_posts_to_search_engine(posts):
    search_logger.info("adding forum posts to solr index")
    search_logger.info("creating XML")
    documents = [convert_to_search_engine_document(p) for p in posts]
    try:
        search_logger.info("posting to search engine")
        search_engine = SearchEngine(settings.SOLR_FORUM_URL)
        search_engine.add_to_index(documents)
    except SearchEngineException as e:
        search_logger.error("failed to add posts to search engine index, reason: %s" % str(e))
    search_logger.info("done")


def add_post_to_search_engine(post_id):
    """Add a forum post to search engine
    Arguments:
        post_id (int): ID of a post object"""

    search_logger.info("adding single forum post to search engine index")
    post = forum.models.Post.objects.select_related("thread", "author", "thread__author", "thread__forum").get(id=post_id)
    send_posts_to_search_engine([post])


def add_all_posts_to_search_engine(slice_size=4000):
    """Add all forum posts to the search engine
    Arguments:
        slice_size (int): The number of posts to send to the search engine at a time"""

    posts = forum.models.Post.objects.select_related("thread", "author", "thread__author", "thread__forum").all()

    num_posts = posts.count()
    for i in range(0, num_posts, slice_size):
        posts_slice = posts[i:i+slice_size]
        send_posts_to_search_engine(posts_slice)


def delete_post_from_search_engine(post_id):
    search_logger.info("deleting post with id %d" % post_id)
    try:
        search_engine = SearchEngine(settings.SOLR_FORUM_URL)
        search_engine.remove_from_index(post_id)
        # solr.commit()
    except SearchEngineException as e:
        search_logger.error('could not delete post with id %s (%s).' % (post_id, e))
