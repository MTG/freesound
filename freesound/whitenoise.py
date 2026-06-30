from django.conf import settings
from whitenoise.middleware import WhiteNoiseMiddleware

DOCS_PREFIX = "/docs/api/"


class FreesoundWhiteNoiseMiddleware(WhiteNoiseMiddleware):
    """Whitenoise Middleware's `add_files` allows you to serve any files from
    a specific directory, but exposes no configuration options for it.
    Whitenoise adds Etag headers, but only adds large cache values for items
    in /static and with a hashed filename, so this is safe for serving html files.
    """

    def __init__(self, get_response=None):
        super().__init__(get_response)
        if getattr(settings, "API_DOCS_ROOT", None):
            self.add_files(settings.API_DOCS_ROOT, prefix=DOCS_PREFIX)
