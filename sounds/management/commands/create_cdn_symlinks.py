import logging
import os
import time

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


CONSECUTIVE_ERROR_LIMIT = 20


class Command(LoggingBaseCommand):
    help = "Create CDN symlinks for all processed sounds that don't have one yet."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sleep",
            type=float,
            default=0.0,
            help="Seconds to sleep between each sound to throttle I/O load (e.g. --sleep=0.01).",
        )

    def handle(self, *args, **options):
        self.log_start()
        sleep_seconds = options["sleep"]
        num_created = 0
        num_skipped = 0
        num_errors = 0
        consecutive_errors = 0

        existing = get_existing_symlinks()
        console_logger.info(f"Found {len(existing)} existing CDN symlinks")

        sounds = Sound.objects.filter(processing_state="OK").order_by("id")
        total = sounds.count()
        console_logger.info(f"Found {total} processed sounds")

        for count, sound in enumerate(sounds.iterator()):
            symlink_name = f"{sound.id}.{sound.type}"
            if symlink_name in existing:
                num_skipped += 1
                consecutive_errors = 0
            else:
                try:
                    if create_cdn_symlink(sound):
                        num_created += 1
                    else:
                        num_skipped += 1
                    consecutive_errors = 0
                except Exception:
                    num_errors += 1
                    consecutive_errors += 1
                    console_logger.exception(f"Error creating symlink for sound {sound.id}")
                    if consecutive_errors >= CONSECUTIVE_ERROR_LIMIT:
                        console_logger.error(
                            f"Aborting: {consecutive_errors} consecutive errors — likely a systemic issue"
                        )
                        break

            if (count + 1) % 5000 == 0:
                console_logger.info(
                    f"[{count + 1}/{total}] Created {num_created}, skipped {num_skipped}, errors {num_errors}"
                )

            if sleep_seconds:
                time.sleep(sleep_seconds)

        console_logger.info(f"Done! Created {num_created}, skipped {num_skipped}, errors {num_errors}")
        self.log_end({"created": num_created, "skipped": num_skipped, "errors": num_errors})
