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

            csv_file_path = os.path.join(output_folder, f"metadata_{id_range_start // 1000:04}.csv")
            with open(csv_file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "id",
                        "username",
                        "title",
                        "description",
                        "tags",
                        "license",
                        "duration",
                        "filesize",
                        "crc32",
                        "bst_category_code",
                        "generative_ai_preference",
                        "created",
                        "avg_rating",
                        "num_ratings",
                        "num_downloads",
                        "num_comments",
                        "pack_name",
                        "type",
                        "geotag",
                    ]
                )
                # Get corresponding Sound objects. include_audio_descriptors=True is used to avoid N+1 queries when accessing the generated bst category (if needed).
                sound_objects = Sound.objects.ordered_ids(sound_ids, include_audio_descriptors=True)
                for sound in sound_objects:
                    fields = [
                        sound.id,
                        sound.username,
                        sound.original_filename,
                        sound.description,
                        " ".join(sound.tag_array),
                        sound.license.name,
                        sound.duration,
                        sound.filesize,
                        sound.crc,
                        sound.category_code,
                        sound.user.profile.get_gen_ai_preference(category_code=sound.category_code),
                        sound.created.strftime("%Y-%m-%d %H:%M:%S"),
                        sound.avg_rating,
                        sound.num_ratings,
                        sound.num_downloads,
                        sound.num_comments,
                        sound.pack_name,
                        sound.type,
                        str(sound.geotag.lat) + " " + str(sound.geotag.lon) if hasattr(sound, "geotag") else "",
                    ]
                    writer.writerow(fields)

                    num_sounds_included += 1
                    if options["limit"] is not None and num_sounds_included >= int(options["limit"]):
                        break

        self.log_end({"num_sounds_included": num_sounds_included, "output_folder": output_folder})
