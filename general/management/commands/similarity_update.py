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
import yaml
import logging
logger = logging.getLogger("web")


class Command(BaseCommand):
    help = "Take all sounds that haven't been added to the similarity service yet and add them. Use option --force to " \
           "force reindex ALL sounds. Pas a number argument to limit the number of sounds that will be reindexed " \
           "(to avoid collapsing similarity if using crons). Pass a string argument with the freesound extractor version" \
           "to only index sounds analyzed with the specified version."
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

        limit = None
        freesound_extractor_version = ''
        for arg in args:
            if arg.isdigit():
                limit = int(arg)
            else:
                freesound_extractor_version = arg

        if options['force']:
            to_be_added = Sound.objects.filter(analysis_state='OK', moderation_state='OK').order_by('id')[:limit]
        else:
            to_be_added = Sound.objects.filter(analysis_state='OK', similarity_state='PE', moderation_state='OK').order_by('id')[:limit]

        logger.info("Starting similarity update. %i sounds to be added to the similarity index" % to_be_added.count())
        N = len(to_be_added)
        for count, sound in enumerate(to_be_added):

            # Check if sound analyzed using the desired extractor
            if freesound_extractor_version:
                try:
                    data = yaml.load(open(sound.locations('analysis.statistics.path')), Loader=yaml.cyaml.CLoader)
                except:
                    print 'Sound with id %i was not indexed (no yaml file found when checking for extractor version)' % sound.id
                    continue

                if data:
                    if 'freesound_extractor' in data['metadata']['version']:
                        if data['metadata']['version']['freesound_extractor'] != freesound_extractor_version:
                            print 'Sound with id %i was not indexed (it was analyzed with extractor version %s)' % (sound.id, data['metadata']['version']['freesound_extractor'])
                            continue
                    else:
                        print 'Sound with id %i was not indexed (it was analyzed with an unknown extractor)' % sound.id
                        continue
                else:
                    print 'Sound with id %i was not indexed (most probably empty yaml file)' % sound.id
                    continue

            try:
                if options['indexing_server']:
                    result = Similarity.add_to_indeixing_server(sound.id, sound.locations('analysis.statistics.path'))
                else:
                    result = Similarity.add(sound.id, sound.locations('analysis.statistics.path'))
                    sound.set_similarity_state('OK')
                print "%s (%i of %i)" % (result, count+1, N)

                # Every 2000 added sounds, save the index
                #if count % 2000 == 0:
                #    if options['indexing_server']:
                #        Similarity.save_indexing_server()
                #    else:
                #        Similarity.save()

            except Exception, e:
                if not options['indexing_server']:
                    sound.set_similarity_state('FA')
                print 'Sound could not be added (id: %i, %i of %i): \n\t%s' % (sound.id, count+1, N ,str(e))

        logger.info("Finished similarity update. %i sounds added to the similarity index" % to_be_added.count())
        # At the end save the index
        #if options['indexing_server']:
        #    Similarity.save_indexing_server()
        #else:
        #    Similarity.save()
