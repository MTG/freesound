#
# Freesound is (c) MUSIC TECHNOLOGY GROUP, UNIVERSITAT POMPEU FABRA
#
# Freesound is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Freesound is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#     See AUTHORS file.
#

import csv
import logging
import os
from datetime import datetime

from django.conf import settings

from sounds.models import Sound
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger("console")


fields = [
    ("id", lambda sound: sound.id),
    ("created", lambda sound: sound.created.strftime("%Y-%m-%d %H:%M:%S")),
    ("username", lambda sound: sound.username),
    ("user_id", lambda sound: sound.user_id),
    ("title", lambda sound: sound.original_filename),
    ("description", lambda sound: sound.description),
    ("tags", lambda sound: " ".join(sound.tag_array)),
    ("pack_name", lambda sound: sound.pack_name),
    ("bst_category_code", lambda sound: sound.category_code),
    ("geotag", lambda sound: sound.geotag.get_lat_lon_as_string() if hasattr(sound, "geotag") else ""),
    ("license", lambda sound: sound.license.name),
    (
        "generative_ai_preference",
        lambda sound: sound.user.profile.get_gen_ai_preference(category_code=sound.category_code),
    ),
    ("type", lambda sound: sound.type),
    ("duration", lambda sound: sound.duration),
    ("filesize", lambda sound: sound.filesize),
    ("crc32", lambda sound: sound.crc),
    ("avg_rating", lambda sound: sound.avg_rating),
    ("num_ratings", lambda sound: sound.num_ratings),
    ("num_downloads", lambda sound: sound.num_downloads),
    ("num_comments", lambda sound: sound.num_comments),
]


class Command(LoggingBaseCommand):
    help = """This command export sounds metadata to a number of .CSV files. These files will be later used to 
    generate the data packs available through the Freesound Data Packs portal."""

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            action="store",
            dest="limit",
            default=None,
            help="Maximum number of sounds to be included. Useful for debugging.",
        )

    def handle(self, *args, **options):
        self.log_start()

        # Generate output folder for the CSV files which should be in the YYYY-MM-DD format
        output_folder = os.path.join(settings.DATA_PACKS_EXPORT_PATH, datetime.now().strftime("%Y-%m-%d"))
        os.makedirs(output_folder, exist_ok=True)

        # Iterate over all Sound objects in chunks of ID//1000 range. Save one .csv metadata file for each chunk so
        # a file has a maximum of 1000 entries. This is done to avoid having a single huge file with all the metadata.

        num_sounds_included = 0
        max_sound_id = Sound.objects.order_by("id").last().id
        for id_range_start in range(0, max_sound_id + 1, 1000):
            if options["limit"] is not None and num_sounds_included >= int(options["limit"]):
                break
            sound_ids = Sound.objects.filter(id__gte=id_range_start, id__lt=id_range_start + 1000).values_list(
                "id", flat=True
            )
            if len(sound_ids) == 0:
                continue

            console_logger.info(
                f"Exporting metadata for sounds with IDs in range [{id_range_start}, {id_range_start + 1000}) - {len(sound_ids)} sounds."
            )

            csv_file_path = os.path.join(output_folder, f"metadata_{id_range_start // 1000:04}.csv")
            with open(csv_file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([h for h, _ in fields])  # Write header row

                # Get corresponding Sound objects. include_audio_descriptors=True is used to avoid N+1 queries when accessing the generated bst category (if needed).
                sound_objects = Sound.objects.ordered_ids(sorted(sound_ids), include_audio_descriptors=True)
                for sound in sound_objects:
                    fields_values = [l(sound) for _, l in fields]
                    writer.writerow(fields_values)
                    num_sounds_included += 1
                    if options["limit"] is not None and num_sounds_included >= int(options["limit"]):
                        break

        self.log_end({"num_sounds_included": num_sounds_included, "output_folder": output_folder})
