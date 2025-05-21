import pytest

def pytest_addoption(parser):
    """Used in the search enging backend tests to select a backend engine"""
    parser.addoption("--search-engine-backend", action="store", default="utils.search.backends.solr9pysolr.Solr9PySolrSearchEngine")

@pytest.fixture
def use_dummy_cache_backend(settings):
    settings.CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        },
        'api_monitoring': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        },
        'clustering': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        },
        'cdn_map': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
}