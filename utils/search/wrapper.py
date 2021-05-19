from django.conf import settings

from utils.search.solr import SolrQuery, Solr, SolrResponseInterpreter, \
    SolrException, BaseSolrAddEncoder, SolrJsonResponseDecoder


class SearchEngine(object):
    def __init__(self, url="http://localhost:8983/solr", verbose=False, persistent=False, 
                 encoder=BaseSolrAddEncoder(), decoder=SolrJsonResponseDecoder()):
        self.backend = Solr(url, verbose, persistent, encoder, decoder)

    def search(self, query):
        return SolrResponseInterpreter(self.backend.select(unicode(query)))

    def add_to_index(self):
        pass

    def remove_from_index(self):
        pass
