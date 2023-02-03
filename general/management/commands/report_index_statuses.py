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

from sounds.models import Sound, SoundAnalysis
from utils.management_commands import LoggingBaseCommand
from utils.search.search_sounds import get_all_sound_ids_from_search_engine, delete_sounds_from_search_engine
from utils.similarity_utilities import Similarity

console_logger = logging.getLogger('console')


class Command(LoggingBaseCommand):
    help = "This command checks the status of the solr and gaia index compared to the fs database. Reports about " \
           "sounds which are missing in gaia and solr and sounds that are in gaia or solr but not in fs dataset. " \
           "Moreover, it changes the status of the sounds in fs dataset that are not in gaia or solr so the next " \
           "time the indexes are updated (running similarity_update and post_dirty_sounds_to_search_engine) they " \
           "are indexed."

    def add_arguments(self, parser):
        parser.add_argument(
            '-n', '--no-changes',
            action='store_true',
            dest='no-changes',
            default=False,
            help='Using the option --no-changes the is_index_dirty and similarity_state sound fields will not '
                 'be modified.')

    def handle(self,  *args, **options):
        self.log_start()

        # Get all solr ids
        console_logger.info("Getting solr ids...")
        solr_ids = get_all_sound_ids_from_search_engine()

        # Get ell gaia ids
        console_logger.info("Getting gaia ids...")
        gaia_ids = Similarity.get_all_sound_ids()

        console_logger.info("Getting freesound db data...")
        # Get all moderated and processed sound ids
        queryset = Sound.objects.filter(processing_state='OK', moderation_state='OK').order_by('id').only("id")
        fs_mp = [sound.id for sound in queryset]
        # Get ell moderated, processed and analysed sounds
        sound_ids_analyzed_with_analyzer_ok = \
            list(SoundAnalysis.objects.filter(analyzer=settings.FREESOUND_ESSENTIA_EXTRACTOR_NAME, analysis_status="OK")
                .values_list('sound_id', flat=True))
        fs_mpa = sorted(list(fs_mp.intersection(sound_ids_analyzed_with_analyzer_ok)))

        in_solr_not_in_fs = list(set(solr_ids).intersection(set(set(solr_ids).difference(fs_mp))))
        in_fs_not_in_solr = list(set(fs_mp).intersection(set(set(fs_mp).difference(solr_ids))))

        messages = []
        messages.append("\nNumber of sounds per index:\n--------------------------")
        messages.append(f"Solr index\t\t{len(solr_ids)}")
        messages.append(f"Gaia index\t\t{len(gaia_ids)}")
        messages.append(f"Freesound\t\t{len(fs_mp)}  (moderated and processed)")
        messages.append(f"Freesound\t\t{len(fs_mpa)}  (moderated, processed and analyzed)")
        messages.append("\n\n***************\nSOLR INDEX\n***************\n")
        messages.append(f"Sounds in solr but not in fs:\t{len(in_solr_not_in_fs)}")
        messages.append(f"Sounds in fs but not in solr:\t{len(in_fs_not_in_solr)}")
        console_logger.info('\n'.join(messages))

        if not options['no-changes']:
            # Mark fs sounds to go processing
            if in_fs_not_in_solr:
                console_logger.info(f"Changing is_index_dirty_state of {len(in_fs_not_in_solr)} sounds")
                Sound.objects.filter(id__in=in_fs_not_in_solr).update(is_index_dirty=True)

            # Delete sounds from solr that are not in the db
            if in_solr_not_in_fs:
                console_logger.info(f"\nDeleting {len(in_solr_not_in_fs)} sounds that should not be in solr")
                delete_sounds_from_search_engine(sound_ids=in_solr_not_in_fs)

        in_gaia_not_in_fs = list(set(gaia_ids).intersection(set(set(gaia_ids).difference(fs_mpa))))
        in_fs_not_in_gaia = list(set(fs_mpa).intersection(set(set(fs_mpa).difference(gaia_ids))))

        messages = []
        messages.append("\n***************\nGAIA INDEX\n***************\n")
        messages.append(f"Sounds in gaia but not in fs:\t{len(in_gaia_not_in_fs)}")
        messages.append("Sounds in fs but not in gaia:\t%i  (only considering sounds correctly analyzed)" \
                   % len(in_fs_not_in_gaia))
        console_logger.info('\n'.join(messages))

        if not options['no-changes']:
            # Mark fs sounds to go processing
            if in_fs_not_in_gaia:
                console_logger.info("Changing similarity_state of sounds that require it")
                N = len(in_fs_not_in_gaia)
                for count, sid in enumerate(in_fs_not_in_gaia):
                    console_logger.info('\r\tChanging state of sound %i of %i         ' % (count+1, N))
                    sound = Sound.objects.get(id=sid)
                    sound.set_similarity_state('PE')

            # Delete sounds from gaia that are not in the db
            if in_gaia_not_in_fs:
                console_logger.info("\nDeleting sounds that should not be in gaia")
                N = len(in_gaia_not_in_fs)
                for count, sid in enumerate(in_gaia_not_in_fs):
                    console_logger.info('\r\tDeleting sound %i of %i         ' % (count+1, N))
                    Similarity.delete(sid)

        self.log_end({
            'n_sounds_in_db_moderated_processed': len(fs_mp),
            'n_sounds_in_db_moderated_processed_analyzed': len(fs_mpa),
            'n_sounds_in_gaia': len(gaia_ids),
            'n_sounds_in_solr': len(solr_ids),
            'n_sounds_in_solr_but_not_in_fs': len(in_solr_not_in_fs),
            'n_sounds_in_fs_but_not_in_solr': len(in_fs_not_in_solr),
            'n_sounds_in_gaia_but_not_in_fs': len(in_gaia_not_in_fs),
            'n_sounds_in_fs_but_not_in_gaia': len(in_fs_not_in_gaia),
        })
