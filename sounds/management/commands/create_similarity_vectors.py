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

from django.conf import settings

from sounds.models import Sound, SoundAnalysis, SoundSimilarityVector
from utils.management_commands import LoggingBaseCommand

console_logger = logging.getLogger("console")


class Command(LoggingBaseCommand):
    help = """This command will create or update SoundSimilarityVector objects for all sounds and for a given similarity space.
    It will also mark all affected sounds as dirty so they are re-indexed.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--similarity-space",
            action="store",
            dest="similarity_space",
            default=None,
            help="Name of the similarity space to consider (default: None, which means all similarity spaces).",
        )

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

        similarity_space_name = options["similarity_space"]
        if similarity_space_name is None:
            similarity_space_names = list(settings.SIMILARITY_SPACES.keys())
        else:
            similarity_space_names = [similarity_space_name]

        n_created = 0
        n_updated = 0
        for count, similarity_space_name in enumerate(similarity_space_names, start=1):
            if similarity_space_name not in settings.SIMILARITY_SPACES:
                raise Exception(f"Similarity space '{similarity_space_name}' not found in settings.SIMILARITY_SPACES")

            console_logger.info(
                f"* Processing similarity space '{similarity_space_name}' [{count}/{len(similarity_space_names)}]"
            )

            sim_space_settings = settings.SIMILARITY_SPACES.get(similarity_space_name, None)
            analyzer_name = sim_space_settings["analyzer"]
            sound_ids_with_analyzer_ok = SoundAnalysis.objects.filter(
                sound_id__in=sound_ids, analyzer=analyzer_name, analysis_status="OK"
            ).values_list("sound_id", flat=True)
            sound_ids = list(set(sound_ids) & set(sound_ids_with_analyzer_ok))

            sound_ids_with_sim_vectors_ok = SoundSimilarityVector.objects.filter(
                similarity_space_name=similarity_space_name
            ).values_list("sound_id", flat=True)

            chunk_size = int(options["chunk_size"])
            sound_ids = sorted(sound_ids)
            total_sounds = len(sound_ids)

            if skip_update:
                # If we are skipping updates, we can filter out sounds that already have a similarity vector objects to avoid unnecessary processing
                sound_ids = [sid for sid in sound_ids if sid not in sound_ids_with_sim_vectors_ok]
                total_sounds = len(sound_ids)

            starttime = time.monotonic()
            total_done = 0
            for i in range(0, total_sounds, chunk_size):
                # Get sound objects for chunk, include audio descriptors to avoid extra db queries
                chunk_sound_ids = sound_ids[i : i + chunk_size]

                chunk_sound_ids_with_existing_sim_vectors_objects = set(chunk_sound_ids) & set(
                    sound_ids_with_sim_vectors_ok
                )
                chunk_sound_ids_without_existing_sim_vectors_objects = set(chunk_sound_ids) - set(
                    chunk_sound_ids_with_existing_sim_vectors_objects
                )

                sounds_dict = Sound.objects.dict_ids(chunk_sound_ids)  # Get sound objects as will be used later
                affected_sound_ids = []

                # UPDATE already existing sim vector objects
                if not skip_update:
                    sim_vector_objects_to_update = SoundSimilarityVector.objects.filter(
                        sound_id__in=chunk_sound_ids_with_existing_sim_vectors_objects,
                        similarity_space_name=similarity_space_name,
                    )
                    n_will_be_updated = 0
                    for ssv in sim_vector_objects_to_update:
                        sim_vector = sounds_dict[ssv.sound_id].load_similarity_vector(
                            similarity_space_name=similarity_space_name, no_db_operations=True
                        )
                        if sim_vector:
                            ssv.vector = sim_vector
                            n_will_be_updated += 1
                            affected_sound_ids.append(ssv.sound_id)
                    SoundSimilarityVector.objects.bulk_update(sim_vector_objects_to_update, ["vector"])
                    n_updated += n_will_be_updated

                # CREATE sim vector objects
                if not skip_create:
                    sim_vector_objects_to_create = []
                    for sid in chunk_sound_ids_without_existing_sim_vectors_objects:
                        sim_vector = sounds_dict[sid].load_similarity_vector(
                            similarity_space_name=similarity_space_name, no_db_operations=True
                        )
                        if sim_vector:
                            sim_vector_objects_to_create.append(
                                SoundSimilarityVector(
                                    sound_id=sid,
                                    similarity_space_name=similarity_space_name,
                                    vector=sim_vector,
                                )
                            )
                            affected_sound_ids.append(sid)
                    SoundSimilarityVector.objects.bulk_create(sim_vector_objects_to_create)
                    n_created += len(sim_vector_objects_to_create)

                # Mark all affected sounds as dirty so re-indexing happens
                if not options["skip_mark_dirty"]:
                    Sound.objects.filter(id__in=affected_sound_ids).update(is_index_dirty=True)

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
