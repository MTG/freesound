import pytest


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