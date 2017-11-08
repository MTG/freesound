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

from solr import Solr, SolrException
from django.conf import settings
import logging

logger = logging.getLogger("search")

def convert_to_solr_document(post):
    #logger.info("creating solr XML from forum post %d" % post.id)
    document = {}

    document["id"] = post.id
    document["thread_id"] = post.thread.id
    document["thread_title"] = post.thread.title
    document["thread_author"] = post.thread.author
    document["thread_created"] = post.thread.created

    document["forum_name"] = post.thread.forum.name
    document["forum_name_slug"] = post.thread.forum.name_slug

    document["post_author"] = post.author
    document["post_created"] = post.created
    document["post_body"] = post.body

    document["num_posts"] = post.thread.num_posts
    document["has_posts"] = False if post.thread.num_posts == 0 else True

    return document


def add_post_to_solr(post):
    logger.info("adding single forum post to solr index")
    try:
        Solr(settings.SOLR_FORUM_URL).add([convert_to_solr_document(post)])
    except SolrException as e:
        logger.error("failed to add forum post %d to solr index, reason: %s" % (post.id, str(e)))


def add_posts_to_solr(posts):
    logger.info("adding multiple forum posts to solr index")
    solr = Solr(settings.SOLR_FORUM_URL, auto_commit=False)


    logger.info("creating XML")
    documents = map(convert_to_solr_document, posts)
    logger.info("posting to Solr")
    solr.add(documents)

    solr.commit()
    logger.info("optimizing solr index")
    #solr.optimize()
    logger.info("done")

def add_all_posts_to_solr(post_queryset, slice_size=4000, mark_index_clean=False):
    # Pass in a queryset to avoid needing a reference to
    # the Post class, it causes circular imports.
    num_posts = post_queryset.count()
    for i in range(0, num_posts, slice_size):
        try:
            posts = post_queryset[i:i+slice_size]
            add_posts_to_solr(posts)
        except SolrException as e:
            logger.error("failed to add post batch to solr index, reason: %s" % str(e))

def delete_post_from_solr(post):
    logger.info("deleting post with id %d" % post.id)
    try:
        Solr(settings.SOLR_FORUM_URL).delete_by_id(post.id)
    except Exception as e:
        logger.error('could not delete post with id %s (%s).' % (post.id, e))
