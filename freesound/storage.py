from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class NoStrictManifestStaticFilesStorage(ManifestStaticFilesStorage):
    manifest_strict = False
