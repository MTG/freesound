import json

from debug_toolbar.panels import Panel
from django.core.cache import cache
from django.template.loader import render_to_string


class SolrDebugPanel(Panel):
    
    name = 'SOLR'
    title= 'SOLR Debug Panel'
    nav_title = 'SOLR'
    template = 'panels/solr.html'
    has_content = True
    
    @property
    def nav_subtitle(self):
        stats = self.get_stats()
        if stats['num_queries']:
            return f"{stats['num_queries']} quer{'y' if stats['num_queries'] == 1 else 'ies'} ({stats['total_time']}ms)"
        return "No queries"
    
    def generate_stats(self, request, response):
        queries_info = cache.get("solr_debug_panel_query_info", [])
        if queries_info is None:
            queries_info = []
        stats = {
            'request_url': request.get_full_path(),
            'request_method': request.method,
            'post_data': json.dumps(request.POST, sort_keys=True, indent=4),
            'queries_info': queries_info,
            'num_queries': len(queries_info),
            'total_time': sum(query['time'] for query in queries_info) if queries_info else 0.0
        }
        self.record_stats(stats)
        cache.delete("solr_debug_panel_query_info") 