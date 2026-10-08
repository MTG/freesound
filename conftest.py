import pytest
from django.core.management import call_command


def pytest_addoption(parser):
    """These options are used in the search enging backend tests, however they are available to all pytests tests (but unused)"""
    parser.addoption(
        "--search-engine-backend", action="store", default="utils.search.backends.solr9pysolr.Solr9PySolrSearchEngine"
    )
    parser.addoption("--write-search-engine-output", action="store_true", default=False)
    parser.addoption(
        "--keep-solr-index", action="store_true", default=False, help="Keep Solr indexes after tests for inspection"
    )


@pytest.fixture
def load_fixtures(db):
    """Return a loader for Django fixtures, e.g. load_fixtures(["licenses", "sounds"])."""

    def load(names: list[str]) -> None:
        call_command("loaddata", *names, verbosity=0)

    return load


@pytest.fixture
def use_dummy_cache_backend(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        },
        "api_monitoring": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        },
        "clustering": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        },
    }
