import os

from django.apps import AppConfig
from django.conf import settings


class GeneralConfig(AppConfig):
    name = "general"

    def ready(self):
        """
        Create the folders (if not already existing) for the base data directory and all needed subdirecotries.
        This code is run here as we want to run it at Django startup.
        """
        os.makedirs(settings.DATA_PATH, exist_ok=True)
        os.makedirs(settings.AVATARS_PATH, exist_ok=True)
        os.makedirs(settings.PREVIEWS_PATH, exist_ok=True)
        os.makedirs(settings.DISPLAYS_PATH, exist_ok=True)
        os.makedirs(settings.SOUNDS_PATH, exist_ok=True)
        os.makedirs(settings.PACKS_PATH, exist_ok=True)
        os.makedirs(settings.UPLOADS_PATH, exist_ok=True)
        os.makedirs(settings.CSV_PATH, exist_ok=True)
        os.makedirs(settings.ANALYSIS_PATH, exist_ok=True)
        os.makedirs(settings.FILE_UPLOAD_TEMP_DIR, exist_ok=True)
        os.makedirs(settings.PROCESSING_TEMP_DIR, exist_ok=True)
        os.makedirs(settings.PROCESSING_BEFORE_DESCRIPTION_DIR, exist_ok=True)
