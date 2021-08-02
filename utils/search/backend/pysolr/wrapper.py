from django.conf import settings

from utils.search.backend.pysolr.client import SolrQuery, Solr, SolrResponseInterpreter, \
    SolrException, BaseSolrAddEncoder, SolrJsonResponseDecoder, SolrResponseInterpreterPaginator, \
    convert_to_solr_document


class SearchEngine(object):
    def __init__(self, url="http://localhost:8983/solr", verbose=False, persistent=False, 
                 encoder=BaseSolrAddEncoder(), decoder=SolrJsonResponseDecoder()):
        self.backend = Solr(url, verbose, persistent, encoder, decoder)

    def search(self, query):
        return SolrResponseInterpreter(self.backend.select(query.as_dict()))
    
    def return_paginator(self, results, num_per_page):
        return SolrResponseInterpreterPaginator(results, num_per_page)

    def add_to_index(self, docs):
        self.backend.add(docs)

    def remove_from_index(self, sound_id):
        self.backend.delete_by_id(sound_id)

    def remove_from_index_by_query(self, query):
        self.backend.delete_by_query(query)

    def remove_documents_by_ids(self, document_ids):
        sound_ids_query = ' OR '.join(['id:{0}'.format(document_id) for document_id in document_ids])
        self.backend.remove_from_index_by_query(sound_ids_query)


class QueryManager(SolrQuery):
    pass


class SearchEngineException(SolrException):
    pass


def convert_to_search_engine_document(document):
    return convert_to_solr_document(document)
