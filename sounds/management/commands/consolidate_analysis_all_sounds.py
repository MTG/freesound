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

import logging

from sounds.models import Sound, SoundAnalysis
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger("console")


class Command(LoggingBaseCommand):
    help = """This script runs consolidate analysis for all sounds in freesound.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--chunk-size",
            action="store",
            dest="chunk_size",
            default=1000,
            help="Number of sounds to process in each chunk (default: 1000).",
        )

    def handle(self, *args, **options):
        self.log_start()
        sound_ids = Sound.objects.all().values_list("id", flat=True).order_by("id")
        chunk_size = int(options["chunk_size"])
        total_sounds = sound_ids.count()
        console_logger.info(f"Total sounds to process: {total_sounds}")

        for i in range(0, total_sounds, chunk_size):
            chunk_sound_ids = sound_ids[i : i + chunk_size]
            console_logger.info(
                f"Processing chunk {i // chunk_size + 1}/{(total_sounds + chunk_size - 1) // chunk_size} (sounds {i + 1} to {min(i + chunk_size, total_sounds)})"
            )

            # Get sound objects for chunk
            sounds_dict = Sound.objects.dict_ids(chunk_sound_ids, include_audio_descriptors=True)

            # We get a list of the existing analyzer objects to avoid having to try file loads for each sound/analyzer pair
            existing_analyzer_objects_ok = (
                SoundAnalysis.objects.filter(sound_id__in=chunk_sound_ids, analysis_status="OK")
                .exclude(analyzer="consolidated")
                .values_list("sound_id", "analyzer")
            )

            ssaa_to_update = SoundAnalysis.objects.filter(sound_id__in=chunk_sound_ids, analyzer="consolidated")
            sound_ids_updated_analysis = [sa.sound_id for sa in ssaa_to_update]

            for sa in ssaa_to_update:
                data = sounds_dict[sa.sound_id].consolidate_analysis(
                    verbose=False,
                    existing_analyzer_object_names=[
                        analyzer for sound_id, analyzer in existing_analyzer_objects_ok if sound_id == sa.sound_id
                    ],
                    no_db_operations=True,  # We don't do db operation for every sound, only update them in bulks
                )
                sa.analysis_data = data

            # Bulk update the corresponding SoundAnalysis objects with the consolidated analysis data for all sounds in the chunk
            SoundAnalysis.objects.bulk_update(ssaa_to_update, ["analysis_data"])

            # Mark all affected sounds as dirty
            Sound.objects.filter(id__in=sound_ids_updated_analysis).update(is_index_dirty=True)

            # Invalidate template caches in case anything shown in the sound pages depends on analysis data (like automatic category)
            for sid in sound_ids_updated_analysis:
                Sound.invalidate_template_caches_static(sid)

            # If sound sound_ids did not have a consolidated analysis object, we create them now
            # In this case, the consolidate_analysis method will already create the SoundAnalysis object and mark sounds as index dirty and invalidate templates
            missing_sound_ids = set(chunk_sound_ids) - set(sound_ids_updated_analysis)
            for sid in missing_sound_ids:
                sounds_dict[sid].consolidate_analysis(
                    verbose=False,
                    existing_analyzer_object_names=[
                        analyzer for sid_, analyzer in existing_analyzer_objects_ok if sid_ == sid
                    ],
                )

        self.log_end()
