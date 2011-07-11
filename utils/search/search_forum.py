'''
Created on Jun 30, 2011

@author: stelios
'''
from solr import Solr, SolrException
from django.conf import settings
import logging
from forum.models import Post

logger = logging.getLogger("search")

def convert_to_solr_document(post):
    logger.info("creating solr XML from forum post %d" % post.id)
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
    
    logger.info(document)

    return document


def add_post_to_solr(post):
    logger.info("adding single forum post to solr index")
    try:
        Solr(settings.SOLR_FORUM_URL).add([convert_to_solr_document(post)])
    except SolrException, e:
        logger.error("failed to add forum post %d to solr index, reason: %s" % (post.id, str(e)))


def add_posts_to_solr(posts):
    logger.info("adding multiple forum posts to solr index")
    solr = Solr(settings.SOLR_FORUM_URL)


    logger.info("creating XML")
    documents = map(convert_to_solr_document, posts)
    logger.info("posting to Solr")
    solr.add(documents)

    logger.info("optimizing solr index")
    solr.optimize()
    logger.info("done")
    
def delete_post_from_solr(post):
    logger.info("deleting post with id %d" % post.id)
    try:
        Solr(settings.SOLR_FORUM_URL).delete_by_id(post.id)
    except Exception, e:
        logger.error('could not delete post with id %s (%s).' % (post.id, e))