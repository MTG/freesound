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


from django.core.management.base import BaseCommand
from optparse import make_option
from utils.search.search_general import get_all_sound_ids_from_solr, delete_sounds_from_solr
from utils.similarity_utilities import Similarity
from sounds.models import Sound
from utils.search.solr import Solr
from django.conf import settings
import sys

class Command(BaseCommand):
    help = "This command checks the status of the solr and gaia index compared to the fs database. Reports about sounds which " \
           "are missing in gaia and solr and sounds that are in gaia or solr but not in fs dataset. Moreover, it changes the status " \
           "of the sounds in fs dataset that are not in gaia or solr so the next time the indexes are updated " \
           "(running similarity_update and post_dirty_sounds_to_solr) they are indexed."

    def add_arguments(self, parser):
        parser.add_argument(
            '-n','--no-changes',
            action='store_true',
            dest='no-changes',
            default=False,
            help='Using the option --no-changes the is_index_dirty and similarity_state sound fields will not be modified.')

    def handle(self,  *args, **options):

        # init
        solr = Solr(settings.SOLR_URL)

        # Get all solr ids
        print "Getting solr ids...",
        solr_ids = get_all_sound_ids_from_solr()
        print "done!"

        # Get ell gaia ids
        print "Getting gaia ids...",
        gaia_ids = Similarity.get_all_sound_ids()
        print "done!"

        print "Getting freesound db data..."
        # Get all moderated and processed sound ids
        queryset = Sound.objects.filter(processing_state='OK', moderation_state='OK').order_by('id').only("id")
        fs_mp = [sound.id for sound in queryset]
        # Get ell moderated, processed and analysed sounds
        queryset = Sound.objects.filter(processing_state='OK', moderation_state='OK', analysis_state='OK').order_by('id').only("id")
        fs_mpa = [sound.id for sound in queryset]
        print "done!"

        print "\nNumber of sounds per index:\n--------------------------"
        print "Solr index\t\t%i" % len(solr_ids)
        print "Gaia index\t\t%i" % len(gaia_ids)
        print "Freesound\t\t%i  (moderated and processed)" % len(fs_mp)
        print "Freesound\t\t%i  (moderated, processed and analyzed)" % len(fs_mpa)

        print "\n\n***************\nSOLR INDEX\n***************\n"
        in_solr_not_in_fs = list(set(solr_ids).intersection(set(set(solr_ids).difference(fs_mp))))
        in_fs_not_in_solr = list(set(fs_mp).intersection(set(set(fs_mp).difference(solr_ids))))
        print "Sounds in solr but not in fs:\t%i" % len(in_solr_not_in_fs)
        print "Sounds in fs but not in solr:\t%i" % len(in_fs_not_in_solr)

        if not options['no-changes']:
            # Mark fs sounds to go processing
            if in_fs_not_in_solr:
                print "Changing is_index_dirty_state of sounds that require it"
                N = len(in_fs_not_in_solr)
                for count, sid in enumerate(in_fs_not_in_solr):
                    sys.stdout.write('\r\tChanging state of sound sound %i of %i         ' % (count+1, N))
                    sys.stdout.flush()
                    sound = Sound.objects.get(id=sid)
                    sound.set_single_field('is_index_dirty', True)

            # Delete sounds from solr that are not in the db
            if in_solr_not_in_fs:
                print "\nDeleting sounds that should not be in solr"
                sys.stdout.write('\r\tDeleting sound %i sounds from solr' % len(in_solr_not_in_fs))
                sys.stdout.flush()
                delete_sounds_from_solr(sound_ids=in_solr_not_in_fs)

        print "\n***************\nGAIA INDEX\n***************\n"
        in_gaia_not_in_fs = list(set(gaia_ids).intersection(set(set(gaia_ids).difference(fs_mpa))))
        in_fs_not_in_gaia = list(set(fs_mpa).intersection(set(set(fs_mpa).difference(gaia_ids))))
        print "Sounds in gaia but not in fs:\t%i" % len(in_gaia_not_in_fs)
        print "Sounds in fs but not in gaia:\t%i  (only considering sounds correctly analyzed)" % len(in_fs_not_in_gaia)
        #Similarity.save()

        if not options['no-changes']:
            # Mark fs sounds to go processing
            if in_fs_not_in_gaia:
                print "Changing similarity_state of sounds that require it"
                N = len(in_fs_not_in_gaia)
                for count, sid in enumerate(in_fs_not_in_gaia):
                    sys.stdout.write('\r\tChanging state of sound %i of %i         ' % (count+1, N))
                    sys.stdout.flush()
                    sound = Sound.objects.get(id=sid)
                    sound.set_similarity_state('PE')

            # Delete sounds from gaia that are not in the db
            if in_gaia_not_in_fs:
                print "\nDeleting sounds that should not be in gaia"
                N = len(in_gaia_not_in_fs)
                for count, sid in enumerate(in_gaia_not_in_fs):
                    sys.stdout.write('\r\tDeleting sound %i of %i         ' % (count+1, N))
                    sys.stdout.flush()
                    Similarity.delete(sid)

                #Similarity.save()










