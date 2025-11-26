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

from utils.search import SearchEngineException, get_search_engine

search_logger = logging.getLogger("search")
console_logger = logging.getLogger("console")


def add_posts_to_search_engine(post_objects, solr_collection_url=None):
    """Add forum posts to search engine

    Args:
        post_objects (List[forum.models.Post]): list (or queryset) of forum Post objects to index

    Returns:
        int: number of sounds added to the index
    """
    num_posts = len(post_objects)
    try:
        search_logger.info("Adding %d posts to search engine" % num_posts)
        get_search_engine(forum_index_url=solr_collection_url).add_forum_posts_to_index(post_objects)
        return num_posts
    except SearchEngineException as e:
        search_logger.info(f"Failed to add posts to search engine index: {str(e)}")
        return 0


def delete_posts_from_search_engine(post_ids, solr_collection_url=None):
    """Delete forum posts from the search engine

    Args:
        post_ids (list[int]): IDs of the forum posts to delete
    """
    console_logger.info(f"Deleting {len(post_ids)} forum posts from search engine")
    search_logger.info(f"Deleting {len(post_ids)} forum posts from search engine")
    try:
        get_search_engine(forum_index_url=solr_collection_url).remove_forum_posts_from_index(post_ids)
    except SearchEngineException as e:
        console_logger.info(f"Could not delete forum posts: {str(e)}")
        search_logger.info(f"Could not delete forum posts: {str(e)}")


def delete_all_posts_from_search_engine(solr_collection_url=None):
    console_logger.info("Deleting ALL forum posts from search engine")
    try:
        get_search_engine(forum_index_url=solr_collection_url).remove_all_forum_posts()
    except SearchEngineException as e:
        console_logger.info(f"Could not delete forum posts: {str(e)}")


def get_all_post_ids_from_search_engine(solr_collection_url=None, page_size=2000):
    """Retrieves the list of all forum post IDs currently indexed in the search engine

    Args:
        page_size: number of post IDs to retrieve per search engine query

    Returns:
        list[int]: list of forum IDs indexed in the search engine
    """
    console_logger.info("Getting all forum post ids from search engine")
    search_engine = get_search_engine(forum_index_url=solr_collection_url)
    solr_ids = []
    solr_count = None
    current_page = 1
    try:
        while solr_count is None or len(solr_ids) < solr_count:
            response = search_engine.search_forum_posts(
                query_filter="*:*", group_by_thread=False, offset=(current_page - 1) * page_size, num_posts=page_size
            )
            solr_ids += [int(element["id"]) for element in response.docs]
            solr_count = response.num_found
            current_page += 1
    except SearchEngineException as e:
        console_logger.info(f"Could retrieve all forum post IDs from search engine: {str(e)}")
    return sorted(solr_ids)
