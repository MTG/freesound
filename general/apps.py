from django.apps import AppConfig
from django.conf import settings
from utils.filesystem import create_directories


class GeneralConfig(AppConfig):
    name = "general"

    def ready(self):
        """
        Create the folders (if not already existing) for the base data directory and all needed subdirecotries.
        This code is run here as we want to run it at Django startup.
        """
        create_directories(settings.DATA_PATH)
        create_directories(settings.AVATARS_PATH)
        create_directories(settings.PREVIEWS_PATH)
        create_directories(settings.DISPLAYS_PATH)
        create_directories(settings.SOUNDS_PATH)
        create_directories(settings.PACKS_PATH)
        create_directories(settings.UPLOADS_PATH)
        create_directories(settings.CSV_PATH)
        create_directories(settings.ANALYSIS_PATH)
        create_directories(settings.FILE_UPLOAD_TEMP_DIR)
        create_directories(settings.PROCESSING_TEMP_DIR)
