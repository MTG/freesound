import logging
import os

from django.conf import settings

from sounds.models import Sound
from utils.cdn import create_cdn_symlink
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger("console")


def get_existing_symlinks():
    """Scan the cdn_sounds directory and return a set of existing symlink basenames (e.g. '456789.wav')."""
    existing = set()
    base = settings.CDN_SOUNDS_SYMLINKS_PATH
    if not os.path.exists(base):
        return existing
    for folder in os.listdir(base):
        folder_path = os.path.join(base, folder)
        if os.path.isdir(folder_path):
            for name in os.listdir(folder_path):
                existing.add(name)
    return existing


class Command(LoggingBaseCommand):
    help = "Create CDN symlinks for all processed sounds that don't have one yet."

    def handle(self, *args, **options):
        self.log_start()
        num_created = 0
        num_skipped = 0

        existing = get_existing_symlinks()
        console_logger.info(f"Found {len(existing)} existing CDN symlinks")

        sounds = Sound.objects.filter(processing_state="OK").order_by("id")
        total = sounds.count()
        console_logger.info(f"Found {total} processed sounds")

        for count, sound in enumerate(sounds.iterator()):
            symlink_name = f"{sound.id}.{sound.type}"
            if symlink_name in existing:
                num_skipped += 1
            else:
                try:
                    if create_cdn_symlink(sound):
                        num_created += 1
                    else:
                        num_skipped += 1
                except Exception:
                    num_skipped += 1

            if (count + 1) % 10000 == 0:
                console_logger.info(f"[{count + 1}/{total}] Created {num_created}, skipped {num_skipped}")

        console_logger.info(f"Done! Created {num_created} symlinks, skipped {num_skipped}")
        self.log_end({"created": num_created, "skipped": num_skipped})
