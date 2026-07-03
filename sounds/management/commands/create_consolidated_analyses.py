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
import time
from collections import defaultdict

from django.utils import timezone

from sounds.models import Sound, SoundAnalysis
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger("console")


class Command(LoggingBaseCommand):
    help = """This command will create or update "consolidated" SoundAnalysis objects for all sounds. It will also mark all affected 
    sounds as dirty so they are re-indexed, and invalidate template caches in case anything shown in the sound pages depends on analysis 
    data (like automatic category).
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--sound-ids",
            action="store",
            dest="sound_ids",
            default=None,
            help="Comma-separated list of sound IDs to consider (default: None, which means all sounds).",
        )

        parser.add_argument(
            "--skip-create",
            action="store_true",
            dest="skip_create",
            default=False,
            help="If set, skip creating objects for sounds that do not have an already existing consolidated analysis object (default: False).",
        )

        parser.add_argument(
            "--skip-update",
            action="store_true",
            dest="skip_update",
            default=False,
            help="If set, skip updating objects for sounds that already have an existing consolidated analysis object (default: False).",
        )

        parser.add_argument(
            "--skip-mark-dirty",
            action="store_true",
            dest="skip_mark_dirty",
            default=False,
            help="If set, skip marking sounds as dirty (default: False).",
        )

        parser.add_argument(
            "--skip-invalidate-template-caches",
            action="store_true",
            dest="skip_invalidate_template_caches",
            default=False,
            help="If set, skip invalidating template caches (default: False).",
        )

        parser.add_argument(
            "--chunk-size",
            action="store",
            dest="chunk_size",
            default=1000,
            help="Number of sounds to process in each chunk (default: 1000).",
        )

    def handle(self, *args, **options):
        self.log_start()
        skip_create = options["skip_create"]
        skip_update = options["skip_update"]
        sound_ids_option = options["sound_ids"]
        if sound_ids_option:
            sound_ids = [int(sid) for sid in sound_ids_option.split(",")]
        else:
            sound_ids = list(Sound.objects.all().values_list("id", flat=True))
        chunk_size = int(options["chunk_size"])
        sound_ids = sorted(sound_ids)
        total_sounds = len(sound_ids)
        n_created = 0
        n_updated = 0

        if skip_update:
            # If we are skipping updates, we can filter out sounds that already have a consolidated analysis object to avoid unnecessary processing
            existing_consolidated_sound_ids = set(
                SoundAnalysis.objects.filter(sound_id__in=sound_ids, analyzer="consolidated").values_list(
                    "sound_id", flat=True
                )
            )
            sound_ids = [sid for sid in sound_ids if sid not in existing_consolidated_sound_ids]
            total_sounds = len(sound_ids)

        starttime = time.monotonic()
        total_done = 0
        for i in range(0, total_sounds, chunk_size):
            # Get sound objects for chunk, include audio descriptors to avoid extra db queries
            chunk_sound_ids = sound_ids[i : i + chunk_size]
            sounds_dict = Sound.objects.dict_ids(chunk_sound_ids, include_audio_descriptors=True)
            affected_sound_ids = []

            # We get a list of the existing analyzer objects to avoid having to try file loads for each sound/analyzer pair
            existing_analyzer_objects_ok = (
                SoundAnalysis.objects.filter(sound_id__in=chunk_sound_ids, analysis_status="OK")
                .exclude(analyzer="consolidated")
                .values_list("sound_id", "analyzer")
            )
            existing_analyzer_object_names_for_sid = defaultdict(list)
            for sid, analyzer in existing_analyzer_objects_ok:
                existing_analyzer_object_names_for_sid[sid].append(analyzer)

            # UPDATE already existing consolidated SoundAnalysis objects
            # Note that even if we are skipping updates, we still need to get the list of sounds ids that would have been updated to
            # avoid creating duplicated consolidated SoundAnalysis objects for those sounds in the next step
            sound_ids_updated = []
            ssaa_to_update = SoundAnalysis.objects.filter(sound_id__in=chunk_sound_ids, analyzer="consolidated")
            sound_ids_updated = [sa.sound_id for sa in ssaa_to_update]
            if not skip_update:
                for sa in ssaa_to_update:
                    data, _ = sounds_dict[sa.sound_id].consolidate_analysis(
                        verbose=False,
                        existing_analyzer_object_names=existing_analyzer_object_names_for_sid[sa.sound_id],
                        no_db_operations=True,  # We don't do db operation for every sound, only update them in bulks
                    )
                    sa.analysis_data = data
                    sa.last_sent_to_queue = timezone.now()
                    sa.last_analyzer_finished = timezone.now()

                # Bulk update the corresponding SoundAnalysis objects with the consolidated analysis data for all sounds in the chunk
                SoundAnalysis.objects.bulk_update(
                    ssaa_to_update, ["last_analyzer_finished", "last_sent_to_queue", "analysis_data"]
                )
                n_updated += len(sound_ids_updated)
                affected_sound_ids += sound_ids_updated

            # CREATE consolidated SoundAnalysis objects for sounds that did not have one
            if not skip_create:
                missing_sound_ids = set(chunk_sound_ids) - set(sound_ids_updated)
                ssaa_to_create = []
                for sid in missing_sound_ids:
                    data, _ = sounds_dict[sid].consolidate_analysis(
                        verbose=False,
                        existing_analyzer_object_names=existing_analyzer_object_names_for_sid[sid],
                        no_db_operations=True,  # We don't do db operation for every sound, only create them in bulks
                    )
                    ssaa_to_create.append(
                        SoundAnalysis(
                            sound_id=sid,
                            analyzer="consolidated",
                            analysis_status="OK",
                            last_sent_to_queue=timezone.now(),
                            last_analyzer_finished=timezone.now(),
                            analysis_data=data,
                        )
                    )
                SoundAnalysis.objects.bulk_create(ssaa_to_create)
                n_created += len(ssaa_to_create)
                affected_sound_ids += missing_sound_ids
            # Mark all affected sounds as dirty so re-indexing happens
            if not options["skip_mark_dirty"]:
                Sound.objects.filter(id__in=affected_sound_ids).update(is_index_dirty=True)

            # Invalidate template caches in case anything shown in the sound pages depends on analysis data (like automatic category)
            if not options["skip_invalidate_template_caches"]:
                for sid in affected_sound_ids:
                    Sound.invalidate_template_caches_static(sid)

            # Print progress information
            total_done += chunk_size
            elapsed = time.monotonic() - starttime
            seconds_remaining = ((total_sounds - total_done) / total_done) * elapsed if total_done > 0 else 0
            if seconds_remaining < 0:
                seconds_remaining = 0
            time_remaining_label = (
                f"{seconds_remaining / 60 / 60:.4f} hours"
                if seconds_remaining > 3600
                else f"{seconds_remaining / 60:.2f} minutes"
            )
            console_logger.info(
                f"Processing chunk {i // chunk_size + 1}/{(total_sounds + chunk_size - 1) // chunk_size} ({n_created} created, {n_updated} updated, {total_done / elapsed:.2f} sounds/second, {time_remaining_label} remaining)"
            )

        self.log_end(
            {
                "n_created": n_created,
                "n_updated": n_updated,
            }
        )
