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

from django.conf import settings

from sounds.models import Sound, SoundSimilarityVector
from utils.management_commands import LoggingBaseCommand
from utils.search.search_sounds import (
    delete_sounds_from_search_engine,
    get_all_sim_vector_sound_ids_from_search_engine,
    get_all_sound_ids_from_search_engine,
)

console_logger = logging.getLogger("console")


class Command(LoggingBaseCommand):
    help = (
        "This command checks the status of the solr index compared to the fs database. Reports about "
        "sounds which are missing in solr and sounds that are in solr but not in fs database. "
        "If needed, it changes the status of the sounds in fs database that are not in solr so the next "
        "time the indexes are updated (running post_dirty_sounds_to_search_engine) they are indexed."
        "It also deletes documents from solr if they correspond to sounds that are not in the fs database."
        "The command also checks sounds that have similarity vectors in the database but which are not"
        "indexed in solr."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "-n",
            "--no-changes",
            action="store_true",
            dest="no-changes",
            default=False,
            help="Using the option --no-changes the is_index_dirty and similarity_state sound fields will not "
            "be modified.",
        )

    def handle(self, *args, **options):
        self.log_start()

        sound_ids_to_mark_as_dirty = []
        solr_sound_ids_to_delete = []

        # Synchronize sounds

        console_logger.info("Getting solr sound ids...")
        solr_sound_ids = get_all_sound_ids_from_search_engine()

        console_logger.info("Getting database (public) sound ids...")
        db_sound_ids = Sound.public.only("id").values_list("id", flat=True)

        in_db_not_in_solr = list(set(db_sound_ids).difference(solr_sound_ids))
        console_logger.info(f"Sounds in db but not in solr:\t{len(in_db_not_in_solr)}")
        # These sounds should be indexed, add them to a list to be marked as index dirty
        sound_ids_to_mark_as_dirty += in_db_not_in_solr

        in_solr_not_in_db = list(set(solr_sound_ids).difference(db_sound_ids))
        console_logger.info(f"Sounds in solr but not in db:\t{len(in_solr_not_in_db)}")
        # These sounds should not be in solr, so we delete them from solr
        solr_sound_ids_to_delete += in_solr_not_in_db

        # Synchronize similarity vectors

        console_logger.info("Getting solr sim vector sound ids...")
        solr_sim_vector_ids = get_all_sim_vector_sound_ids_from_search_engine()

        console_logger.info("Getting database sim vector sound ids...")
        db_sim_vector_ids = {}
        for similarity_space_name in settings.SIMILARITY_SPACES.keys():
            ids = (
                SoundSimilarityVector.objects.filter(similarity_space_name=similarity_space_name)
                .only("sound_id")
                .values_list("sound_id", flat=True)
            )
            db_sim_vector_ids[similarity_space_name] = ids

        for similarity_space_name in settings.SIMILARITY_SPACES.keys():
            console_logger.info(f"- Processing similarity space: {similarity_space_name}")
            solr_ids = solr_sim_vector_ids.get(similarity_space_name, [])
            db_ids = db_sim_vector_ids[similarity_space_name]
            db_ids = list(
                set(db_ids).intersection(solr_sound_ids)
            )  # Only consider public sounds that are already in solr

            in_db_not_in_solr = list(set(db_ids).difference(solr_ids))
            console_logger.info(f"Sounds with sim vectors in db but not in solr:\t{len(in_db_not_in_solr)}")
            # These sounds should be indexed, add them to a list to be marked as index dirty
            sound_ids_to_mark_as_dirty += in_db_not_in_solr

            in_solr_not_in_db = list(set(solr_ids).difference(db_ids))
            console_logger.info(f"Sim vectors in solr but not in db:\t{len(in_solr_not_in_db)}")
            # These sim vectors should not be in solr, but we don't have a proper way to remove them individually, so we remove the sound
            # from solr and also mark it as index dirty so it gets properly re-indexed next time
            solr_sound_ids_to_delete += in_solr_not_in_db
            sound_ids_to_mark_as_dirty += in_solr_not_in_db

        if not options["no-changes"]:
            console_logger.info("")

            # Mark needed sounds as index dirty
            sound_ids_to_mark_as_dirty = list(set(sound_ids_to_mark_as_dirty))
            if sound_ids_to_mark_as_dirty:
                console_logger.info(f"* Marking {len(sound_ids_to_mark_as_dirty)} sounds as index dirty")
                Sound.objects.filter(id__in=sound_ids_to_mark_as_dirty).update(is_index_dirty=True)

            # Delete unneeded sounds from solr
            solr_sound_ids_to_delete = list(set(solr_sound_ids_to_delete))
            if solr_sound_ids_to_delete:
                console_logger.info(f"* Deleting {len(solr_sound_ids_to_delete)} documents from solr")
                delete_sounds_from_search_engine(sound_ids=solr_sound_ids_to_delete)
                # Note that the above function will also delete similarity vector documents if the "sound id" actually corresponds to a sim vector document id

        self.log_end(
            {
                "n_sounds_marked_as_index_drity": len(sound_ids_to_mark_as_dirty),
                "n_sounds_deleted_in_solr": len(solr_sound_ids_to_delete),
            }
        )
