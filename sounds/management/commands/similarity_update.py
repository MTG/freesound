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
from sounds.models import Sound
from similarity.client import Similarity
from optparse import make_option

class Command(BaseCommand):
    help = "Take all sounds that haven't been added to the similarity service yet and add them. Use option --force to force reindex ALL sounds. Pas a number argument to limit the number of sounds that will be reindexed (to avoid collapsing similarity if using crons)"
    option_list = BaseCommand.option_list + (
    make_option('-f','--force',
        dest='force',
        action='store_true',
        default=False,
        help='Reindex all sounds regardless of their similarity state'),
    )
    option_list += (
    make_option('-i','--indexing_server',
        dest='indexing_server',
        action='store_true',
        default=False,
        help='Send files to the indexing server instead of the main similarity server'),
    )

    def handle(self,  *args, **options):

        end = 100000000000 # Big enough numebr so num_sounds will never exceed this one
        if args:
            limit = args[0]
            if limit:
                end = int(limit)
            print "Indexing sounds to similarity (limit %i)"%end

        if options['force']:
            to_be_added = Sound.objects.filter(analysis_state='OK', moderation_state='OK').order_by('id')[0:end]
        else:
            to_be_added = Sound.objects.filter(analysis_state='OK', similarity_state='PE', moderation_state='OK').order_by('id')[0:end]

        '''
        We should first add a sound which we know it is correctly analyzed
        '''
        #sound = Sound.objects.get(id=1234)
        #if options['indexing_server']:
        #    result = Similarity.add_to_indeixing_server(sound.id, sound.locations('analysis.statistics.path'))
        #else:
        #    result = Similarity.add(sound.id, sound.locations('analysis.statistics.path'))


        for sound in to_be_added:
            try:
                if options['indexing_server']:
                    result = Similarity.add_to_indeixing_server(sound.id, sound.locations('analysis.statistics.path'))
                else:
                    result = Similarity.add(sound.id, sound.locations('analysis.statistics.path'))

                #sound.similarity_state = 'OK'
                sound.set_similarity_state('OK')
                print result
            except Exception, e:
                print 'Sound could not be added (id: %i): \n\t%s' % (sound.id, str(e))
                #sound.similarity_state = 'FA'
                sound.set_similarity_state('FA')
            #sound.save()

        # At the end save the index
        if options['indexing_server']:
            Similarity.save_indexing_server()
        else:
            Similarity.save()