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

from django.conf import settings
from piston.handler import BaseHandler
from piston.utils import rc
from search.forms import SoundSearchForm, SEARCH_SORT_OPTIONS_API
from search.views import search_prepare_sort, search_prepare_query
from sounds.models import Sound, Pack, Download
from bookmarks.models import Bookmark, BookmarkCategory
from utils.search.solr import Solr, SolrQuery, SolrException, SolrResponseInterpreter, SolrResponseInterpreterPaginator
import logging
from django.contrib.auth.models import User
from utils.search.search import add_all_sounds_to_solr
from django.contrib.sites.models import Site
from utils.pagination import paginate
from django.core.urlresolvers import reverse
from utils.nginxsendfile import sendfile
import yaml
from utils.similarity_utilities import get_similar_sounds, query_for_descriptors
from similarity.client import Similarity
from api.api_utils import auth, ReturnError#, parse_filter, parse_target
import os
from django.contrib.syndication.views import Feed
from urllib import quote
from django.core.cache import cache

logger = logging.getLogger("api")

# UTILITY FUNCTIONS

def my_quote(s):
    return quote(s,safe=":[]*+()'")

def prepend_base(rel):
    return "http://%s%s" % (Site.objects.get_current().domain, rel)

def get_sound_api_url(id):
    return prepend_base(reverse('api-single-sound', args=[id]))

def get_sound_api_analysis_url(id):
    return prepend_base(reverse('api-sound-analysis', args=[id]))

def get_sound_web_url(username, id):
    return prepend_base(reverse('sound', args=[username, id]))
    
def get_user_api_url(username):
    return prepend_base(reverse('api-single-user', args=[username]))

def get_user_web_url(username):
    return prepend_base(reverse('account', args=[username]))

def get_bookmark_category_api_url(username, category_id):
    return prepend_base(reverse('api-user-bookmark-category', args=[username, category_id]))

def get_bookmark_category_web_url(username, category_id):
    return prepend_base(reverse('bookmarks-for-user-for-category', args=[username, category_id]))

def get_user_sounds_api_url(username):
    return prepend_base(reverse('api-user-sounds', args=[username]))

def get_user_packs_api_url(username):
    return prepend_base(reverse('api-user-packs', args=[username]))

def get_user_bookmark_categories_api_url(username):
    return prepend_base(reverse('api-user-bookmark-categories', args=[username]))

def get_pack_api_url(pack_id):
    return prepend_base(reverse('api-single-pack', args=[pack_id]))

def get_pack_web_url(username, pack_id):
    return prepend_base(reverse('pack', args=[username, pack_id]))

def get_pack_sounds_api_url(pack_id):
    return prepend_base(reverse('api-pack-sounds', args=[pack_id]))

def get_sound_links(sound):
    ref = get_sound_api_url(sound.id)

    d = {
        'ref': ref,
        'url': get_sound_web_url(sound.user.username, sound.id),
        'serve': ref+'serve/',
        'preview-hq-mp3'   : prepend_base(sound.locations("preview.HQ.mp3.url")),
        'preview-hq-ogg'   : prepend_base(sound.locations("preview.HQ.ogg.url")),
        'preview-lq-mp3'   : prepend_base(sound.locations("preview.LQ.mp3.url")),
        'preview-lq-ogg'   : prepend_base(sound.locations("preview.LQ.ogg.url")),
        'waveform_m': prepend_base(sound.locations("display.wave.M.url")),
        'waveform_l': prepend_base(sound.locations("display.wave.L.url")),
        'spectral_m': prepend_base(sound.locations("display.spectral.M.url")),
        'spectral_l': prepend_base(sound.locations("display.spectral.L.url")),
        'analysis_stats': get_sound_api_analysis_url(sound.id),
        'analysis_frames': prepend_base(sound.locations("analysis.frames.url")),
        'similarity': ref+'similar/',
         }
    if sound.pack_id:
        d['pack'] = get_pack_api_url(sound.pack_id)
    return d

def prepare_minimal_user(user):
    return {'username': user.username,
            'ref': get_user_api_url(user.username),
            'url': get_user_web_url(user.username),}

def prepare_single_sound(sound):
    d = {}
    for field in ["num_downloads", "channels", "duration", "samplerate", "samplerate", \
                  "id", "num_comments", "num_ratings", "filesize", \
                  "type", "description", "bitdepth", "bitrate",  "created", \
                  "avg_rating", "original_filename"]:
        d[field] = getattr(sound, field)
    try:
        d['license'] = sound.license.deed_url
    except:
        pass
    try:
        d['geotag'] = {'lat':sound.geotag.lat,'lon':sound._geotag_cache.lon}
    except:
        pass
    d['user'] = prepare_minimal_user(sound.user)
    d['tags'] = get_tags(sound)
    d.update(get_sound_links(sound))
    return d

def prepare_collection_sound(sound, include_user=True, include_geotag=False, custom_fields = False, extra_properties = None):
    if not custom_fields:
        d = {}
        for field in ["duration", "type", "original_filename", "id"]:
            d[field] = getattr(sound, field)
        if include_user:
            d['user'] = prepare_minimal_user(sound.user)
        d['tags'] = get_tags(sound)
        
        if include_geotag:
            try:
                d['geotag'] = {'lat':sound.geotag.lat,'lon':sound._geotag_cache.lon}
            except:
                pass

        d.update(get_sound_links(sound))

        if extra_properties:
            d.update(extra_properties)

        return d
    else:
        single_sound_prepared = prepare_single_sound(sound)
        if extra_properties:
            single_sound_prepared.update(extra_properties)

        custom_fields = custom_fields.split(",")
        d = {}
        for field in custom_fields:
            if field in single_sound_prepared.keys():
                d[field] = single_sound_prepared[field]
        return d

def prepare_single_sound_analysis(sound,request,filter):

    try:
        analysis = yaml.load(file(sound.locations('analysis.statistics.path')))

        # delete nonsensical/faulty descriptors
        del analysis['lowlevel']['silence_rate_20dB']
        del analysis['lowlevel']['silence_rate_30dB']
        del analysis['rhythm']['bpm_confidence']
        del analysis['rhythm']['perceptual_tempo']
        del analysis['metadata']['tags']
        
        # put the moods in one place
        moods = {'c': {}, 'm': {}}
        for m in ['happy', 'aggressive', 'sad', 'relaxed']:
            moods['c'][m] = analysis['highlevel']['mood_%s' % m]
            del analysis['highlevel']['mood_%s' % m]
        analysis['highlevel']['moods'] = moods
        # rename the mood descriptors that aren't actually moods
        for m in ['party', 'acoustic', 'electronic']:
            analysis['highlevel'][m] = \
                analysis['highlevel']['mood_%s' % m]
            del analysis['highlevel']['mood_%s' % m]
        # put all the genre descriptors in analysis['highlevel']['genre']
        analysis['highlevel']['genre'] = {}
        # rename the genre descriptors
        genre_mappings = {'rosamerica':  {'hip': 'hiphop',
                                          'rhy': 'rnb',
                                          'jaz': 'jazz',
                                          'dan': 'dance',
                                          'roc': 'rock',
                                          'cla': 'classical',
                                          'spe': 'speech'},
                          'dortmund':    {'raphiphop': 'hiphop',
                                          'funksoulrnb': 'rnb',
                                          'folkcountry': 'country'},
                          'tzanetakis':  {'hip': 'hiphop',
                                          'jaz': 'jazz',
                                          'blu': 'blues',
                                          'roc': 'rock',
                                          'cla': 'classical',
                                          'met': 'metal',
                                          'cou': 'country',
                                          'reg': 'reggae',
                                          'dis': 'disco'},
                           'electronica': {}}
        for name,mapping in genre_mappings.items():
            genre_orig = analysis['highlevel']['genre_%s' % name]
            for key,val in mapping.items():
                if key is not val:
                    genre_orig['all'][val] = genre_orig['all'][key]
                    del genre_orig['all'][key]
            if genre_orig['value'] in mapping:
                genre_orig['value'] = mapping[genre_orig['value']]
            analysis['highlevel']['genre'][name[0]] = genre_orig
            del analysis['highlevel']['genre_%s' % name]
        # rename the mirex clusters
        mirex_mapping = {'Cluster1': 'passionate',
                         'Cluster2': 'cheerful',
                         'Cluster3': 'melancholic',
                         'Cluster4': 'humorous',
                         'Cluster5': 'aggressive'}
        for key,val in mirex_mapping.items():
            analysis['highlevel']['mood']['all'][val] = \
                analysis['highlevel']['mood']['all'][key]
            del analysis['highlevel']['mood']['all'][key]
        analysis['highlevel']['mood']['value'] = \
            mirex_mapping[analysis['highlevel']['mood']['value']]
        analysis['highlevel']['moods']['m'] = \
            analysis['highlevel']['mood']
        del analysis['highlevel']['mood']


    except Exception, e:
        raise e
        raise Exception('Could not load analysis data.')

    # only show recommended descriptors
    print request.GET
    if not ('all' in request.GET and request.GET['all'] in ['1', 'true', 'True']):
        analysis = level_filter(analysis, RECOMMENDED_DESCRIPTORS)

    if filter:
        filters = filter.split('/')
        filters = [str(x) for x in filters if x != u'']
        while len(filters) > 0:
            try:
                analysis = analysis.get(filters[0], None)
                if analysis == None:
                    raise Exception('No data here')
                filters = filters[1:]
            except:
                raise ReturnError(400, "InvalidRequest", {"explanation": "Could not find this path in the analysis data."})

    return analysis


def level_filter(d, fields, sep='.'):
    new_d = {}
    for f in fields:
        fs = f.split(sep)
        level_filter_set(new_d, fs, level_filter_get(d, fs))
    return new_d

def level_filter_set(d, levels, value):
    if len(levels) <= 0:
        return d
    if len(levels) == 1:
        d[levels[0]] = value
    else:
        if not d.has_key(levels[0]):
            d[levels[0]] = {}
        level_filter_set(d[levels[0]], levels[1:], value)
    return d

def level_filter_get(d, levels):
    if len(levels) <= 0:
        return d
    if len(levels) == 1:
        return d.get(levels[0], '')
    else:
        return level_filter_get(d[levels[0]], levels[1:])


RECOMMENDED_DESCRIPTORS = [ 'metadata.audio_properties',
                            'highlevel.culture',
                            'highlevel.gender',
                            'highlevel.moods',
                            'highlevel.timbre',
                            'highlevel.voice_instrumental',
                            'highlevel.acoustic',
                            'highlevel.electronic',
                            'tonal.key_key',
                            'tonal.key_scale',
                            'tonal.key_strength',
                            'tonal.tuning_frequency',
                            'rhythm.bpm',
                            'lowlevel.average_loudness',
                            'lowlevel.dissonance.mean',
                            'lowlevel.pitch.mean',
                            'lowlevel.pitch_salience.mean',
                            'lowlevel.spectral_centroid.mean',
                            'lowlevel.mfcc.mean'
                            ]

def get_tags(sound):
    return [tagged.tag.name for tagged in sound.tags.select_related("tag").all()]

def prepare_single_user(user):
    d = {}
    for field in ["username", "first_name", "last_name", "date_joined"]:
        d[field] = getattr(user, field)
    d['ref'] = get_user_api_url(user.username)
    d['url'] = get_user_web_url(user.username)
    d['about'] = user.profile.about
    d['home_page'] = user.profile.home_page
    d['signature'] = user.profile.signature
    d['sounds'] = get_user_sounds_api_url(user.username)
    d['packs'] = get_user_packs_api_url(user.username)
    d['bookmark_categories'] = get_user_bookmark_categories_api_url(user.username)
    return d

def prepare_single_pack(pack, include_user=True, include_description=False):
    d = {}
    for field in ["name", "num_downloads", "created"]:
        d[field] = getattr(pack, field)
    user = User.objects.get(id=pack.user_id)
    if include_user:
        d['user'] = prepare_minimal_user(user)
    if include_description:
        d['description'] = pack.description
    d['ref'] = get_pack_api_url(pack.id)
    d['url'] = get_pack_web_url(user.username, pack.id)
    d['sounds'] = get_pack_sounds_api_url(pack.id)
    return d

def prepare_single_bookmark_category(username, category):
    d = {}
    d['id'] = category.id
    d['name'] = category.name
    d['url'] = get_bookmark_category_web_url(username, category.id)
    d['sounds'] = get_bookmark_category_api_url(username, category.id)
    return d

def find_api_option(cleaned_sort):
    for t in SEARCH_SORT_OPTIONS_API:
        if t[1] == cleaned_sort:
            return t[0]
    return None

def add_request_id(request,result):
    if request.GET.get('request_id', '') != '':
        result['request_id'] = request.GET.get('request_id', '')

# HANDLERS

class SoundSearchHandler(BaseHandler):
    '''
    api endpoint:   /sounds/search
    '''
    allowed_methods = ('GET',)

    '''
    input:          q, f, p, s
    output:         #paginated_search_results#
    curl:           curl http://www.freesound.org/api/sounds/search/?q=hoelahoep
    '''

    @auth()
    def read(self, request):
        
        form = SoundSearchForm(SEARCH_SORT_OPTIONS_API, request.GET)
        if not form.is_valid():
            resp = rc.BAD_REQUEST
            resp.content = form.errors
            return resp

        cd = form.cleaned_data
        grouping = request.GET.get('g', "")
        if grouping == "0":
            grouping = ""

        solr = Solr(settings.SOLR_URL)
        sounds_per_page = min(int(request.GET.get('sounds_per_page', settings.SOUNDS_PER_API_RESPONSE)),settings.MAX_SOUNDS_PER_API_RESPONSE)
        query = search_prepare_query(cd['q'],
                                     cd['f'],
                                     search_prepare_sort(cd['s'], SEARCH_SORT_OPTIONS_API),
                                     cd['p'],
                                     sounds_per_page,
                                     grouping = grouping)

        try:
            results = SolrResponseInterpreter(solr.select(unicode(query)))
            paginator = SolrResponseInterpreterPaginator(results,sounds_per_page)
            page = paginator.page(form.cleaned_data['p'])
            sounds = []
            bad_results = 0
            for object in page['object_list'] :
                try:
                    sound = prepare_collection_sound(Sound.objects.select_related('user').get(id=object['id']), custom_fields = request.GET.get('fields', False))
                    if 'more_from_pack' in object.keys():
                        if object['more_from_pack'] > 0:
                            link = prepend_base(reverse('api-search')+'?q=%s&f=pack:"%s" %s&s=%s&g=%s' % (my_quote(cd['q']),object['pack_name'],my_quote(cd['f']),cd['s'],""))
                            if request.GET.get('sounds_per_page', None):
                                link += "&sounds_per_page=" +  str(request.GET.get('sounds_per_page', None))
                            if request.GET.get('fields', False):
                                link += "&fields=" + str(request.GET.get('fields', False))
                            sound['results_from_the_same_pack'] = link
                            sound['n_results_from_the_same_pack'] = object['more_from_pack']
                    sounds.append(sound)
                except: # This will happen if there are synchronization errors between solr index and the database. In that case sounds are ommited and both num_results and results per page might become inacurate
                    pass
            result = {'sounds': sounds, 'num_results': paginator.count - bad_results, 'num_pages': paginator.num_pages}

            # construct previous and next urls
            if page['has_other_pages']:
                if page['has_previous']:
                    result['previous'] = self.__construct_pagination_link(cd['q'],
                                                                          page['previous_page_number'],
                                                                          cd['f'],
                                                                          find_api_option(cd['s']),
                                                                          request.GET.get('sounds_per_page', None),
                                                                          request.GET.get('fields', False),
                                                                          grouping)
                if page['has_next']:
                    result['next'] = self.__construct_pagination_link(cd['q'],
                                                                      page['next_page_number'],
                                                                      cd['f'],
                                                                      find_api_option(cd['s']),
                                                                      request.GET.get('sounds_per_page',None),
                                                                      request.GET.get('fields', False),
                                                                      grouping)
            add_request_id(request,result)
            logger.info("Searching,q=" + cd['q'] + ",f=" + cd['f'] + ",p=" + str(cd['p']) + ",sounds_per_page=" + str(sounds_per_page) + ",api_key=" + request.GET.get("api_key", False) + ",api_key_username=" + request.user.username)
            return result

        except SolrException, e:
            error = "search_query %s filter_query %s sort %s error %s" \
                        % (cd['s'], cd['f'], cd['s'], e)
            raise ReturnError(500, "SearchError", {"explanation": error})


    def __construct_pagination_link(self, q, p, f, s, spp, fields, grouping):
        link = prepend_base(reverse('api-search')+'?q=%s&p=%s&f=%s&s=%s&g=%s' % (my_quote(q),p,my_quote(f),s,grouping))
        if spp:
            link += "&sounds_per_page=" +  str(spp)
        if fields:
            link += "&fields=" + str(fields)
        return link


class SoundContentSearchHandler(BaseHandler):
    '''
    api endpoint:   /sounds/content_search
    '''
    allowed_methods = ('GET',)

    '''
    input:          t, f, p
    output:         #paginated_search_results#
    curl:           curl http://www.freesound.org/api/sounds/content_search/?t=".lowlevel.pitch.mean:220.56"
    '''

    @auth()
    def read(self, request):
        t = request.GET.get("t", "")
        f = request.GET.get("f", "")

        if not t and not f:
            raise ReturnError(400, "BadRequest", {"explanation": "Introduce either a target, a filter or both."})
        try:
            results = query_for_descriptors(t,f, int(request.GET.get('max_results', settings.SOUNDS_PER_PAGE)))
        except Exception, e:
            if str(e)[0:6] == u"Target" or str(e)[0:6] == u"Filter":
                raise ReturnError(400, "BadRequest", {'explanation':e})
            else:
                raise ReturnError(500, "ContentBasedSearchError", {'explanation':'Unknown error 500'})

        paginator = paginate(request, results, min(int(request.GET.get('sounds_per_page', settings.SOUNDS_PER_API_RESPONSE)),settings.MAX_SOUNDS_PER_API_RESPONSE),'p')
        page = paginator['page']
        sounds = []
        if int(request.GET.get("p", "1")) <= paginator['paginator'].num_pages: # This is to mimic solr paginator behavior
            for result in page.object_list:
                try:
                    sound = prepare_collection_sound(Sound.objects.select_related('user').get(id=int(result[0])), include_user=False, custom_fields = request.GET.get('fields', False))
                    sounds.append(sound)
                except Exception, e:
                    # Delete sound from gaia index so it does not appear again in similarity searches
                    if Similarity.contains(int(result[0])):
                        Similarity.delete(int(result[0]))
                    # Invalidate similarity search cache
                    cache_key = "content-based-search-t-%s-f-%s-nr-%s" % (t.replace(" ",""),f.replace(" ",""),int(request.GET.get('max_results', settings.SOUNDS_PER_PAGE)))
                    cache.delete(cache_key)

        #sounds = [prepare_collection_sound(Sound.objects.select_related('user').get(id=int(result[0])), include_user=False, custom_fields = request.GET.get('fields', False)) for result in page.object_list]
        result = {'sounds': sounds,  'num_results': paginator['paginator'].count, 'num_pages': paginator['paginator'].num_pages}

        if int(request.GET.get("p", "1")) <= paginator['paginator'].num_pages: # This is to mimic solr paginator behavior
            if page.has_other_pages():
                if page.has_previous():
                    result['previous'] = self.__construct_pagination_link(str(t), str(f), page.previous_page_number(), request.GET.get('sounds_per_page',None), int(request.GET.get('max_results', False)), request.GET.get('fields', False))
                if page.has_next():
                    result['next'] = self.__construct_pagination_link(str(t), str(f), page.next_page_number(), request.GET.get('sounds_per_page',None), int(request.GET.get('max_results', False)), request.GET.get('fields', False))

        add_request_id(request,result)

        logger.info("Content searching, t=" + str(t) + ", f=" + str(f) + ", api_key=" + request.GET.get("api_key", False) + ",api_key_username=" + request.user.username)
        return result

    def __construct_pagination_link(self, t, f, p, spp, num_results, fields):

        link = prepend_base(reverse('api-content-search')+'?t=%s&f=%s&p=%s' % (my_quote(t.replace('"',"'")),my_quote(f.replace('"',"'")),p))#get_user_sounds_api_url(u)+'?p=%s' % p
        if spp:
            link += "&sounds_per_page=" + str(spp)
        if num_results:
            link += "&max_results=" + str(num_results)
        if fields:
            link += "&fields=" + str(fields)
        return link


class SoundHandler(BaseHandler):
    '''
    api endpoint:   /sounds/<sound_id>
    '''
    allowed_methods = ('GET',)

    '''
    input:          n.a.
    output:         #single_sound#
    curl:           curl http://www.freesound.org/api/sounds/2
    '''

    @auth()
    def read(self, request, sound_id):

        try:
            sound = Sound.objects.select_related('geotag', 'user', 'license', 'tags').get(id=sound_id, moderation_state="OK", processing_state="OK")
        except Sound.DoesNotExist: #@UndefinedVariable
            raise ReturnError(404, "NotFound", {"explanation": "Sound with id %s does not exist." % sound_id})

        result = prepare_single_sound(sound)

        add_request_id(request,result)
        logger.info("Sound info,id=" + sound_id + ",api_key=" + request.GET.get("api_key", False) + ",api_key_username=" + request.user.username)
        return result

class SoundServeHandler(BaseHandler):
    '''
    api endpoint:    /sounds/serve|preview
    '''
    allowed_methods = ('GET',)

    '''
    input:        n.a.
    output:       binary file
    curl:         curl http://www.freesound.org/api/sounds/2/serve
    '''

    @auth()
    def read(self, request, sound_id):
        
        try:
            sound = Sound.objects.get(id=sound_id, moderation_state="OK", processing_state="OK")            
        except Sound.DoesNotExist: #@UndefinedVariable
            raise ReturnError(404, "NotFound", {"explanation": "Sound with id %s does not exist." % sound_id})
        
        # Check if file actually exists in the hard drive
        if not os.path.exists(sound.locations('path')) :
            raise ReturnError(404, "NotFound", {"explanation": "Sound with id %s is not available for download." % sound_id})
        
        # DISABLED (FOR THE MOMENT WE DON'T UPDATE DOWNLOADS TABLE THROUGH API)
        #Download.objects.get_or_create(user=request.user, sound=sound, interface='A')
        
        logger.info("Serving sound,id=" + sound_id + ",api_key=" + request.GET.get("api_key", False) + ",api_key_username=" + request.user.username)
        return sendfile(sound.locations("path"), sound.friendly_filename(), sound.locations("sendfile_url"))


class SoundSimilarityHandler(BaseHandler):
    '''
    api endpoint:    /sounds/<sound_id>/similarity
    '''
    allowed_methods = ('GET',)

    '''
    input:        n.a.
    output:       #collection_of_similar_sounds#
    curl:         curl http://www.freesound.org/api/sounds/2/similar
    '''

    @auth()
    def read(self, request, sound_id):
        
        try:
            sound = Sound.objects.get(id=sound_id, moderation_state="OK", processing_state="OK", similarity_state="OK")
            #TODO: similarity_state="OK"
            #TODO: this filter has to be added again, but first the db has to be updated

        except Sound.DoesNotExist: #@UndefinedVariable
            raise ReturnError(404, "NotFound", {"explanation": "Sound with id %s does not exist or similarity data is not ready." % sound_id})

        similar_sounds = get_similar_sounds(sound,request.GET.get('preset', None), int(request.GET.get('num_results', settings.SOUNDS_PER_PAGE)) )

        sounds = []
        for similar_sound in similar_sounds :
            try:
                sound = prepare_collection_sound(Sound.objects.select_related('user').get(id=similar_sound[0]), custom_fields = request.GET.get('fields', False))
                sound['distance'] = similar_sound[1]
                sounds.append(sound)
            except Exception, e:
                # Delete sound from gaia index so it does not appear again in similarity searches
                if Similarity.contains(similar_sound[0]):
                    Similarity.delete(similar_sound[0])
                # Invalidate similarity search cache
                cache_key = "similar-for-sound-%s-%s" % (similar_sound[0], request.GET.get('preset', None))
                cache.delete(cache_key)

        result = {'sounds': sounds, 'num_results': len(sounds)}
        add_request_id(request,result)
        logger.info("Sound similarity,id=" + sound_id + ",api_key=" + request.GET.get("api_key", False) + ",api_key_username=" + request.user.username)
        return result



class SoundAnalysisHandler(BaseHandler):
    '''
    api endpoint:   /sounds/<sound_id>/analysis/<filter>
    '''
    allowed_methods = ('GET',)

    '''
    input:          n.a.
    output:         #single_sound_analysis#
    curl:           curl http://www.freesound.org/api/sounds/2/analysis
    '''

    @auth()
    def read(self, request, sound_id, filter=False):

        try:
            sound = Sound.objects.select_related('geotag', 'user', 'license', 'tags').get(id=sound_id, moderation_state="OK", analysis_state="OK")
        except Sound.DoesNotExist: #@UndefinedVariable
            raise ReturnError(404, "NotFound", {"explanation": "Sound with id %s does not exist or analysis data is not ready." % sound_id})
        
        # TODO: check 404 in http://tabasco.upf.edu/api/sounds/52749/analysis/?api_key=*

        result = prepare_single_sound_analysis(sound,request,filter)

        add_request_id(request,result)
        logger.info("Sound analysis,id=" + sound_id + ",api_key=" + request.GET.get("api_key", False) + ",api_key_username=" + request.user.username)
        return result

"""
# For future use (when we serve analysis files through autenthication)
class SoundAnalysisFramesHandler(BaseHandler):
    '''
    api endpoint:   /sounds/<sound_id>/analysis_frames
    '''
    allowed_methods = ('GET',)

    '''
    #input:          n.a.
    #output:         binary file
    #curl:           curl http://www.freesound.org/api/sounds/2/analysis_frames
    '''

    def read(self, request, sound_id, filter=False):

        try:
            sound = Sound.objects.select_related('geotag', 'user', 'license', 'tags').get(id=sound_id, moderation_state="OK", analysis_state="OK")
        except Sound.DoesNotExist: #@UndefinedVariable
            resp = rc.NOT_FOUND
            resp.content = 'There is no sound with id %s or analysis is not ready' % sound_id
            return resp

        return sendfile(sound.locations('analysis.frames.path'), sound.friendly_filename().split('.')[0] + '.json', sound.locations("sendfile_url").split('.')[0] + '.json')
"""

class SoundGeotagHandler(BaseHandler):
    '''
    api endpoint:   /sounds/geotag/
    '''
    allowed_methods = ('GET',)

    '''
    input:          min_lat, max_lat, min_lon, max_lon, p
    output:         #paginated_sound_results#
    curl:           curl http://www.freesound.org/api/sounds/geotag/?min_lon=2.005176544189453&max_lon=2.334766387939453&min_lat=41.3265528618605&max_lat=41.4504467428547
    '''

    @auth()
    def read(self, request):
        
        min_lat = request.GET.get('min_lat', 0.0)
        max_lat = request.GET.get('max_lat', 0.0)
        min_lon = request.GET.get('min_lon', 0.0)
        max_lon = request.GET.get('max_lon', 0.0)
        
        if min_lat <= max_lat and min_lon <= max_lon:
            raw_sounds = Sound.objects.select_related("geotag").exclude(geotag=None).filter(moderation_state="OK", processing_state="OK").filter(geotag__lat__range=(min_lat,max_lat)).filter(geotag__lon__range=(min_lon,max_lon))
        elif min_lat > max_lat and min_lon <= max_lon:
            raw_sounds = Sound.objects.select_related("geotag").exclude(geotag=None).filter(moderation_state="OK", processing_state="OK").exclude(geotag__lat__range=(max_lat,min_lat)).filter(geotag__lon__range=(min_lon,max_lon))
        elif min_lat <= max_lat and min_lon > max_lon:
            raw_sounds = Sound.objects.select_related("geotag").exclude(geotag=None).filter(moderation_state="OK", processing_state="OK").filter(geotag__lat__range=(min_lat,max_lat)).exclude(geotag__lon__range=(max_lon,min_lon))
        elif min_lat > max_lat and min_lon > max_lon:
            raw_sounds = Sound.objects.select_related("geotag").exclude(geotag=None).filter(moderation_state="OK", processing_state="OK").exclude(geotag__lat__range=(max_lat,min_lat)).exclude(geotag__lon__range=(max_lon,min_lon))
        else:
            return ReturnError(400, "BadRequest", {"explanation": "Parameters min_lat, max_lat, min_long and max_log are not correctly defined."})

        paginator = paginate(request, raw_sounds, min(int(request.GET.get('sounds_per_page', settings.SOUNDS_PER_API_RESPONSE)),settings.MAX_SOUNDS_PER_API_RESPONSE), 'p')
        page = paginator['page']
        if int(request.GET.get("p", "1")) <= paginator['paginator'].num_pages: # This is to mimic solr paginator behavior
            sounds = [prepare_collection_sound(sound, include_user=True, include_geotag=True, custom_fields = request.GET.get('fields', False)) for sound in page.object_list]
        else:
            sounds = []
        result = {'sounds': sounds, 'num_results': paginator['paginator'].count, 'num_pages': paginator['paginator'].num_pages}
        if int(request.GET.get("p", "1")) <= paginator['paginator'].num_pages: # This is to mimic solr paginator behavior
            if page.has_other_pages():
                if page.has_previous():
                    result['previous'] = self.__construct_pagination_link(page.previous_page_number(), min_lon, max_lon, min_lat, max_lat, request.GET.get('sounds_per_page',None), request.GET.get('fields', False))
                if page.has_next():
                    result['next'] = self.__construct_pagination_link(page.next_page_number(), min_lon, max_lon, min_lat, max_lat, request.GET.get('sounds_per_page',None), request.GET.get('fields', False))

        add_request_id(request,result)
        logger.info("Geotags search,min_lat=" + str(min_lat) + ",max_lat=" + str(max_lat) + ",min_lon=" + str(min_lon) + ",max_lon=" + str(max_lon) + ",api_key=" + request.GET.get("api_key", False) + ",api_key_username=" + request.user.username)
        return result

    def __construct_pagination_link(self, p, min_lon, max_lon, min_lat, max_lat, spp, fields):
        link = prepend_base(reverse('api-sound-geotag')) + '?p=%s&min_lon=%s&max_lon=%s&min_lat=%s&max_lat=%s' % (p,min_lon,max_lon,min_lat,max_lat)
        if spp:
            link += "&sounds_per_page=" + str(spp)
        if fields:
            link += "&fields=" + str(fields)
        return link

class UserHandler(BaseHandler):
    '''
    api endpoint:   /people/<username>
    '''
    allowed_methods = ('GET',)

    '''
    input:          n.a.
    output:         #single_user#
    curl:           curl http://www.freesound.org/api/people/vincent_akkermans
    '''

    @auth()
    def read(self, request, username):
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            raise ReturnError(404, "NotFound", {"explanation": "User (%s) does not exist." % username})

        result = prepare_single_user(user)

        add_request_id(request,result)
        logger.info("User info,username=" + username + ",api_key=" + request.GET.get("api_key", False) + ",api_key_username=" + request.user.username)
        return result

class UserSoundsHandler(BaseHandler):
    '''
    api endpoint:   /people/<username>/sounds
    '''
    allowed_methods = ('GET',)

    '''
    input:          p, c
    output:         #user_sounds#
    curl:           curl http://www.freesound.org/api/people/vincent_akkermans/sounds?p=5
    '''

    @auth()
    def read(self, request, username):
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            raise ReturnError(404, "NotFound", {"explanation": "User (%s) does not exist." % username})

        paginator = paginate(request, Sound.public.filter(user=user, processing_state="OK", moderation_state="OK"), min(int(request.GET.get('sounds_per_page', settings.SOUNDS_PER_API_RESPONSE)),settings.MAX_SOUNDS_PER_API_RESPONSE), 'p')
        page = paginator['page']
        if int(request.GET.get("p", "1")) <= paginator['paginator'].num_pages: # This is to mimic solr paginator behavior
            sounds = [prepare_collection_sound(sound, include_user=True, custom_fields = request.GET.get('fields', False)) for sound in page.object_list]
        else:
            sounds = []
        result = {'sounds': sounds,  'num_results': paginator['paginator'].count, 'num_pages': paginator['paginator'].num_pages}

        if int(request.GET.get("p", "1")) <= paginator['paginator'].num_pages: # This is to mimic solr paginator behavior
            if page.has_other_pages():
                if page.has_previous():
                    result['previous'] = self.__construct_pagination_link(username, page.previous_page_number(), request.GET.get('sounds_per_page',None), request.GET.get('fields', False))
                if page.has_next():
                    result['next'] = self.__construct_pagination_link(username, page.next_page_number(), request.GET.get('sounds_per_page',None), request.GET.get('fields', False))

        add_request_id(request,result)
        logger.info("User sounds,username=" + username + ",api_key=" + request.GET.get("api_key", False) + ",api_key_username=" + request.user.username)
        return result

    #TODO: auth() ?
    def __construct_pagination_link(self, u, p, spp, fields):
        link = get_user_sounds_api_url(u)+'?p=%s' % p
        if spp:
            link += "&sounds_per_page=" + str(spp)
        if fields:
            link += "&fields=" + str(fields)
        return link

class UserPacksHandler(BaseHandler):
    '''
    api endpoint:   /people/<username>/packs
    '''
    allowed_methods = ('GET',)

    '''
    input:          n.a.
    output:         #user_packs#
    curl:           curl http://www.freesound.org/api/people/vincent_akkermans/packs
    '''

    @auth()
    def read(self, request, username):
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            raise ReturnError(404, "NotFound", {"explanation": "User (%s) does not exist." % username})

        packs = [prepare_single_pack(pack, include_user=False) for pack in Pack.objects.filter(user=user)]
        result = {'packs': packs, 'num_results': len(packs)}

        add_request_id(request,result)
        logger.info("User packs,username=" + username + ",api_key=" + request.GET.get("api_key", False) + ",api_key_username=" + request.user.username)
        return result

class UserBookmarkCategoriesHandler(BaseHandler):
    '''
    api endpoint:   /people/<username>/bookmark_categories
    '''
    allowed_methods = ('GET',)

    '''
    input:          n.a.
    output:         #user_bookmark_categories#
    curl:           curl http://www.freesound.org/api/people/vincent_akkermans/bookmark_categories
    '''

    @auth()
    def read(self, request, username):
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            raise ReturnError(404, "NotFound", {"explanation": "User (%s) does not exist." % username})

        categories = [prepare_single_bookmark_category(username, category) for category in BookmarkCategory.objects.filter(user=user)]
        # Add uncategorized category (if uncategorized bookmarks exist)
        if Bookmark.objects.select_related("sound").filter(user=user,category=None).count():
            categories.append({
                'name':'Uncategorized bookmarks',
                'url':get_user_bookmark_categories_api_url(username),
                'sounds':prepend_base(reverse('api-user-bookmark-uncategorized', args=[username]))
            })

        result = {'categories': categories, 'num_results': len(categories)}

        add_request_id(request,result)
        logger.info("User bookmark categories,username=" + username + ",api_key=" + request.GET.get("api_key", False) + ",api_key_username=" + request.user.username)
        return result

class UserBookmarkCategoryHandler(BaseHandler):
    '''
    api endpoint:   /people/<username>/bookmark_categories/<category_id>/sounds/
    '''
    allowed_methods = ('GET',)

    '''
    input:          n.a.
    output:         #user_bookmark_category_sounds#
    curl:           curl http://www.freesound.org/api/people/vincent_akkermans/bookmark_categories/34/sounds/
    '''

    @auth()
    def read(self, request, username, category_id = None):
        try:
            user = User.objects.get(username__iexact=username)
            if category_id:
                category = BookmarkCategory.objects.get(user__username__iexact=username, id=category_id )
        except BookmarkCategory.DoesNotExist:
            raise ReturnError(404, "NotFound", {"explanation": "Bookmark category with id %s does not exist." % category_id})
        except User.DoesNotExist:
            raise ReturnError(404, "NotFound", {"explanation": "User (%s) does not exist." % username})

        if category_id:
            bookmarked_sounds = category.bookmarks.select_related("sound").all()
        else:
            bookmarked_sounds = Bookmark.objects.select_related("sound").filter(user=user,category=None)

        paginator = paginate(request, bookmarked_sounds, min(int(request.GET.get('sounds_per_page', settings.SOUNDS_PER_API_RESPONSE)),settings.MAX_SOUNDS_PER_API_RESPONSE), 'p')
        page = paginator['page']
        if int(request.GET.get("p", "1")) <= paginator['paginator'].num_pages: # This is to mimic solr paginator behavior
            sounds = [prepare_collection_sound(bookmark.sound, include_user=True, custom_fields = request.GET.get('fields', False), extra_properties={'bookmark_name':bookmark.name}) for bookmark in page.object_list]
        else:
            sounds = []
        result = {'sounds': sounds, 'num_results': paginator['paginator'].count, 'num_pages': paginator['paginator'].num_pages}
        if int(request.GET.get("p", "1")) <= paginator['paginator'].num_pages: # This is to mimic solr paginator behavior
            if page.has_other_pages():
                if page.has_previous():
                    result['previous'] = self.__construct_pagination_link(username, category_id, page.previous_page_number())
                if page.has_next():
                    result['next'] = self.__construct_pagination_link(username, category_id, page.next_page_number())

        add_request_id(request,result)
        logger.info("User bookmarks for category,username=" + username + ",category_id=" + str(category_id) + ",api_key=" + request.GET.get("api_key", False) + ",api_key_username=" + request.user.username)
        return result

    def __construct_pagination_link(self, username, category_id, p):
        return get_bookmark_category_api_url(username,category_id)+'?p=%s' % p

class PackHandler(BaseHandler):
    '''
    api endpoint:   /packs/<pack_id>
    '''
    allowed_methods = ('GET',)

    '''
    input:          n.a.
    output:         #user_packs#
    curl:           curl http://www.freesound.org/api/packs/<pack_id>
    '''

    @auth()
    def read(self, request, pack_id):
        try:
            pack = Pack.objects.get(id=pack_id)
        except Pack.DoesNotExist:
            raise ReturnError(404, "NotFound", {"explanation": "Pack with id %s does not exist." % pack_id})

        result = prepare_single_pack(pack, include_description=True)

        add_request_id(request,result)
        logger.info("Pack info,id=" + pack_id + ",api_key=" + request.GET.get("api_key", False) + ",api_key_username=" + request.user.username)
        return result

class PackSoundsHandler(BaseHandler):
    '''
    api endpoint:   /packs/<pack_id>/sounds
    '''
    allowed_methods = ('GET',)

    '''
    input:          p
    output:         #pack_sounds#
    curl:           curl http://www.freesound.org/api/packs/<pack_id>/sounds
    '''

    @auth()
    def read(self, request, pack_id):
        try:
            pack = Pack.objects.get(id=pack_id)
        except User.DoesNotExist:
            raise ReturnError(404, "NotFound", {"explanation": "Pack with id %s does not exist." % pack_id})

        paginator = paginate(request, Sound.objects.filter(pack=pack.id, processing_state="OK", moderation_state="OK"), min(int(request.GET.get('sounds_per_page', settings.SOUNDS_PER_API_RESPONSE)),settings.MAX_SOUNDS_PER_API_RESPONSE), 'p')
        page = paginator['page']
        if int(request.GET.get("p", "1")) <= paginator['paginator'].num_pages: # This is to mimic solr paginator behavior
            sounds = [prepare_collection_sound(sound, include_user=True, custom_fields = request.GET.get('fields', False)) for sound in page.object_list]
        else:
            sounds = []
        result = {'sounds': sounds, 'num_results': paginator['paginator'].count, 'num_pages': paginator['paginator'].num_pages}
        if int(request.GET.get("p", "1")) <= paginator['paginator'].num_pages: # This is to mimic solr paginator behavior
            if page.has_other_pages():
                if page.has_previous():
                    result['previous'] = self.__construct_pagination_link(pack_id, page.previous_page_number(),request.GET.get('sounds_per_page', None), request.GET.get('fields', False))
                if page.has_next():
                    result['next'] = self.__construct_pagination_link(pack_id, page.next_page_number(),request.GET.get('sounds_per_page', None), request.GET.get('fields', False))

        add_request_id(request,result)
        logger.info("Pack sounds,id=" + pack_id + ",api_key=" + request.GET.get("api_key", False) + ",api_key_username=" + request.user.username)
        return result

    def __construct_pagination_link(self, pack_id, p, spp, fields):
        link = get_pack_sounds_api_url(pack_id)+'?p=%s' % p
        if spp:
            link += "&sounds_per_page=" + str(spp)
        if fields:
            link += "&fields=" + str(fields)

        return link


class PackServeHandler(BaseHandler):
    '''
    api endpoint:    /packs/id/serve
    '''
    allowed_methods = ('GET',)

    '''
    input:        n.a.
    output:       binary file
    curl:         curl http://www.freesound.org/api/packs/2/serve
    '''

    @auth()
    def read(self, request, pack_id):
        try:
            pack = Pack.objects.get(id=pack_id)
        except Pack.DoesNotExist:
            raise ReturnError(404, "NotFound", {"explanation": "Pack with id %s does not exist." % pack_id})

        logger.info("Serving pack,id=" + pack_id + ",api_key=" + request.GET.get("api_key", False) + ",api_key_username=" + request.user.username)
        return sendfile(pack.locations("path"), pack.friendly_filename(), pack.locations("sendfile_url"))



# N.B. don't add this to a production environment!
class UpdateSolrHandler(BaseHandler):
    allowed_methods = ('GET',)

    @auth()
    def read(self, request):
        sound_qs = Sound.objects.select_related("pack", "user", "license") \
                                .filter(processing_state="OK", moderation_state="OK")
        add_all_sounds_to_solr(sound_qs)
        return rc.ALL_OK


# Pool handlers (RSS)
class SoundPoolSearchHandler(Feed):
    title = "Freesound"
    link = "http://freesound.org/"

    def get_object(self, request):
        type = request.GET.get('type', 'all')
        query = request.GET.get('query', '')
        limit = request.GET.get('limit', 20)
        offset = request.GET.get('offset', 0)
        return {'type':type,'query':query,'limit':limit,'offset':offset}

    def items(self, obj):
        if obj['query'] != "": 
            try:
                solr = Solr(settings.SOLR_URL)
                query = SolrQuery()
                fields=[('id',4),
                        ('tag', 3),
                        ('description', 3),
                        ('username', 2),
                        ('pack_tokenized', 2),
                        ('original_filename', 2),]
                
                
                if obj['type'] == "phrase":
                    query.set_dismax_query('"' + obj['query'] + '"',query_fields=fields) # EXACT (not 100%)    
                elif obj['type'] == "any":
                    query.set_dismax_query(obj['query'],query_fields=[],minimum_match=0) # OR
                else:
                    query.set_dismax_query(obj['query'],query_fields=[],minimum_match="100%") # AND
                
                lim = obj['limit']
                if lim > 100:
                    lim = 100
                
                    
                query.set_query_options(start=obj['offset'], rows=lim, filter_query="", sort=['created desc'])
                
                try:
                    results = SolrResponseInterpreter(solr.select(unicode(query)))
                    
                    sounds = []
                    for object in results.docs :
                        try:
                            sounds.append(object)
                        except: # This will happen if there are synchronization errors between solr index and the database. In that case sounds are ommited and both num_results and results per page might become inacurate
                            pass

                    logger.info("Sound pool search RSS")
                    return sounds
        
                except SolrException, e:
                    return []
            except:
                return []
        else:
            return []

    def item_title(self, item):
        return item['original_filename']

    def item_description(self, item):
        tags = item['tag']
        s= "Tags: "
        for t in tags:
            s = s + t + " "
        s += "<br>"
        desc = item['description']
        s = s + desc
        return s
        
    def item_link(self, item):
        return "http://freesound.org/people/" + str(item['username']) + "/sounds/" + str(item['id'])
        
    def item_author_name(self, item):
        return item['username']
        
    def item_author_link(self, item):
        return "http://freesound.org/people/" + str(item['username'])
         
    def item_pubdate(self, item):
        return item['created']


class SoundPoolInfoHandler(Feed):
    title = "Freesound"
    link = "http://freesound.org/"

    def items(self):
        logger.info("Sound pool info RSS")
        return []

    def item_title(self, item):
        return ""

    def item_description(self, item):
        return ""
