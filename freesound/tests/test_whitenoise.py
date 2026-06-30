from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from freesound.whitenoise import DOCS_PREFIX, FreesoundWhiteNoiseMiddleware


def get_response(request):
    return HttpResponse("fallback", status=418)


class TestFreesoundWhiteNoiseMiddleware:
    """Check that docs are reachable under the /docs/api/ prefix and that the docs
    HTML is served with revalidation headers but without the forever/immutable
    cache that Whitenoise only applies to hashed files under the static prefix.
    """

    @contextmanager
    def make_middleware(self):
        with TemporaryDirectory() as tmp_dir:
            docs_root = Path(tmp_dir)
            (docs_root / "index.html").write_text("api docs index")
            (docs_root / "resources_apiv2.html").write_text("api docs resources")

            settings_override = {
                "API_DOCS_ROOT": str(docs_root),
                "DEBUG": True,
                "STATIC_ROOT": "",
                "WHITENOISE_AUTOREFRESH": True,
                "WHITENOISE_INDEX_FILE": True,
                "WHITENOISE_MAX_AGE": 60,
                "WHITENOISE_ROOT": None,
                "WHITENOISE_USE_FINDERS": False,
            }
            with override_settings(**settings_override):
                yield FreesoundWhiteNoiseMiddleware(get_response), RequestFactory()

    def test_serves_api_docs_under_prefix(self):
        with self.make_middleware() as (middleware, factory):
            index_response = middleware(factory.get(DOCS_PREFIX))
            assert index_response.status_code == 200
            assert b"".join(index_response.streaming_content) == b"api docs index"

            page_response = middleware(factory.get(f"{DOCS_PREFIX}resources_apiv2.html"))
            assert page_response.status_code == 200
            assert b"".join(page_response.streaming_content) == b"api docs resources"

    def test_docs_html_has_revalidation_but_not_immutable_cache(self):
        with self.make_middleware() as (middleware, factory):
            response = middleware(factory.get(f"{DOCS_PREFIX}resources_apiv2.html"))

            # An ETag is present so browsers can revalidate the HTML.
            assert response.has_header("ETag")

            # The docs live outside the static prefix, so they must not receive the
            # forever/immutable Cache-Control that Whitenoise reserves for hashed
            # static files; they get the short configured max-age instead.
            cache_control = response.headers.get("Cache-Control", "")
            assert "immutable" not in cache_control
            assert cache_control == "max-age=60, public"
