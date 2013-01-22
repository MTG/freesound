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
from utils.search.solr import Solr, SolrResponseInterpreter, SolrQuery
import settings
import sys

def list_of_dicts_to_list_of_ids(ldicts):
    return [x['id'] for x in ldicts]


class Command(BaseCommand):
    args = ''
    help = 'Get ids from solr index and remove the ones corresponding the sounds that are NOT in the PG db'

    def handle(self, *args, **options):

        LIMIT = None
        SLICE_SIZE = 500
        solr_sound_ids = []
        solr = Solr(url=settings.SOLR_URL)
        query = SolrQuery()
        query.set_dismax_query("") # Query to get ALL sounds

        print "Retrieving ids from %i to %i"%(0,SLICE_SIZE)
        query.set_query_options(field_list=["id"], rows = SLICE_SIZE, start = 0)
        results = SolrResponseInterpreter(solr.select(unicode(query)))
        solr_sound_ids += list_of_dicts_to_list_of_ids(results.docs)
        total_num_documents = results.num_found

        # Start iterating over other pages (slices)
        if LIMIT:
            number_of_documents = min(LIMIT,total_num_documents)
        else:
            number_of_documents = total_num_documents

        for i in range(SLICE_SIZE,number_of_documents,SLICE_SIZE):
            print "Retrieving ids from %i to %i"%(i,i+SLICE_SIZE)
            query.set_query_options(field_list=["id"], rows = SLICE_SIZE, start = i)
            results = SolrResponseInterpreter(solr.select(unicode(query)))
            solr_sound_ids += list_of_dicts_to_list_of_ids(results.docs)

        solr_sound_ids = sorted(list(set(solr_sound_ids)))
        if LIMIT:
            solr_sound_ids = solr_sound_ids[0:LIMIT]
        print "%i document ids retrieved"%len(solr_sound_ids)
        n_deleted = 0
        print ""
        for count,id in enumerate(solr_sound_ids):
            sys.stdout.write("\rChecking doc %i of %i"%(count,len(solr_sound_ids)))
            sys.stdout.flush()

            if Sound.objects.filter(id=id,moderation_state="OK",processing_state="OK").exists():
                pass
            else:
                # Sound does not exist in the Db or is not properly moderated and processed
                print "\n\t - Deleting sound with id %i from solr index"%id
                solr.delete_by_id(id)
                n_deleted += 1

        print "\n\nDONE! %i sounds deleted from solr index (it may take some minutes to actually see the changes in the page)"%n_deleted




