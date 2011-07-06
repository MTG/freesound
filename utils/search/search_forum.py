'''
Created on Jun 30, 2011

@author: stelios
'''
from solr import Solr, SolrException
from django.conf import settings
import logging
from forum.models import Post

logger = logging.getLogger("search")

def convert_to_solr_document(thread):
    logger.info("creating solr XML from forum thread %d" % thread.id)
    document = {}

    document["id"] = thread.forum.id
    document["forum_name"] = thread.forum.name
    document["forum_name_slug"] = thread.forum.name_slug
    
    document["username"] = thread.author.username
    
    document["thread_name"] = thread.title
    document["created"] = thread.created
    document["num_posts"] = thread.num_posts
    
    # TODO: revise the below and choose fields
    document["post"] =  list(Post.objects.filter(thread=thread).values_list(flat=True))
    document["has_posts"] = False if thread.num_posts == 0 else True 
    
    logger.info(document)

    return document


def add_thread_to_solr(thread):
    logger.info("adding single forum thread to solr index")
    try:
        Solr(settings.SOLR_FORUM_URL).add([convert_to_solr_document(thread)])
    except SolrException, e:
        logger.error("failed to add forum thread %d to solr index, reason: %s" % (thread.id, str(e)))


def add_threads_to_solr(threads):
    logger.info("adding multiple forum threads to solr index")
    solr = Solr(settings.SOLR_FORUM_URL)


    logger.info("creating XML")
    documents = map(convert_to_solr_document, threads)
    logger.info("posting to Solr")
    solr.add(documents)

    logger.info("optimizing solr index")
    solr.optimize()
    logger.info("done")
    
def delete_thread_from_solr(thread):
    logger.info("deleting thread with id %d" % thread.id)
    try:
        Solr(settings.SOLR_FORUM_URL).delete_by_id(thread.id)
    except Exception, e:
        logger.error('could not delete thread with id %s (%s).' % (thread.id, e))