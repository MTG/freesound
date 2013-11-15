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

from solr import Solr, SolrException, SolrResponseInterpreter
import sounds
from django.conf import settings
from freesound.search.views import search_prepare_sort, search_prepare_query
from freesound.search.forms import SEARCH_SORT_OPTIONS_API
import logging

logger = logging.getLogger("search")

def convert_to_solr_document(sound):
    logger.info("creating solr XML from sound %d" % sound.id)
    document = {}

    document["id"] = sound.id
    document["username"] = sound.user.username
    document["created"] = sound.created
    document["original_filename"] = sound.original_filename

    document["description"] = sound.description
    document["tag"] = list(sound.tags.select_related("tag").values_list('tag__name', flat=True))

    document["license"] = sound.license.name

    document["is_remix"] = bool(sound.sources.count())
    document["was_remixed"] = bool(sound.remixes.count())


    if sound.pack:
        document["pack"] = sound.pack.name
        document["grouping_pack"] = str(sound.pack.id) + "_" + sound.pack.name
    else:
        document["grouping_pack"] = str(sound.id)


    document["is_geotagged"] = sound.geotag_id != None

    document["type"] = sound.type

    document["duration"] = sound.duration
    document["bitdepth"] = sound.bitdepth if sound.bitdepth != None else 0
    document["bitrate"] = sound.bitrate if sound.bitrate != None else 0
    document["samplerate"] = int(sound.samplerate)
    document["filesize"] = sound.filesize
    document["channels"] = sound.channels
    document["md5"] = sound.md5

    document["num_downloads"] = sound.num_downloads

    document["avg_rating"] = sound.avg_rating
    document["num_ratings"] = sound.num_ratings

    document["comment"] = list(sound.comments.values_list('comment', flat=True))
    document["comments"] = sound.num_comments

    document["waveform_path_m"] = sound.locations()["display"]["wave"]["M"]["path"]
    document["waveform_path_l"] = sound.locations()["display"]["wave"]["L"]["path"]
    document["spectral_path_m"] = sound.locations()["display"]["spectral"]["M"]["path"]
    document["spectral_path_l"] = sound.locations()["display"]["spectral"]["L"]["path"]
    document["preview_path"] = sound.locations()["preview"]["LQ"]["mp3"]["path"]

    return document


def add_sound_to_solr(sound):
    logger.info("adding single sound to solr index")
    try:
        Solr(settings.SOLR_URL).add([convert_to_solr_document(sound)])
    except SolrException, e:
        logger.error("failed to add sound %d to solr index, reason: %s" % (sound.id, str(e)))


def add_sounds_to_solr(sounds):
    logger.info("adding multiple sounds to solr index")
    solr = Solr(settings.SOLR_URL)


    logger.info("creating XML")
    documents = map(convert_to_solr_document, sounds)
    logger.info("posting to Solr")
    solr.add(documents)

    logger.info("optimizing solr index")
    #solr.optimize()
    logger.info("done")


def add_all_sounds_to_solr(sound_queryset, slice_size=4000, mark_index_clean=False):
    # Pass in a queryset to avoid needing a reference to
    # the Sound class, it causes circular imports.
    num_sounds = sound_queryset.count()
    for i in range(0, num_sounds, slice_size):
        print "Adding %i sounds to solr, slice %i"%(slice_size,i)
        try:
            sounds_to_update = sound_queryset[i:i+slice_size]
            add_sounds_to_solr(sounds_to_update)
            if mark_index_clean:
                logger.info("Marking sounds as clean.")
                sounds.models.Sound.objects.filter(pk__in=[snd.id for snd in sounds_to_update]).update(is_index_dirty=False)
        except SolrException, e:
            logger.error("failed to add sound batch to solr index, reason: %s" % str(e))


def get_all_sound_ids_from_solr():
    logger.info("getting all sound ids from solr.")
    solr = Solr(settings.SOLR_URL)
    solr_ids = []
    solr_count = None
    PAGE_SIZE = 100000
    current_page = 1
    try:
        while len(solr_ids) < solr_count or solr_count == None:
            print "Getting page %i" % current_page
            response = SolrResponseInterpreter(solr.select(unicode(search_prepare_query('', '', search_prepare_sort('created asc', SEARCH_SORT_OPTIONS_API), current_page, PAGE_SIZE, include_facets=False))))
            solr_ids += [element['id'] for element in response.docs]
            solr_count = response.num_found
            current_page += 1
    except Exception, e:
        raise Exception(e)

    return sorted(solr_ids)


def delete_sound_from_solr(sound):
    logger.info("deleting sound with id %d" % sound.id)
    try:
        Solr(settings.SOLR_URL).delete_by_id(sound.id)
    except Exception, e:
        logger.error('could not delete sound with id %s (%s).' % (sound.id, e))
