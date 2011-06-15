from django.conf import settings
from piston.handler import BaseHandler
from piston.utils import rc
from search.forms import SoundSearchForm, SEARCH_SORT_OPTIONS_API
from search.views import search_prepare_sort, search_prepare_query
from sounds.models import Sound, Pack, Download
from utils.search.solr import Solr, SolrException, SolrResponseInterpreter, SolrResponseInterpreterPaginator
import logging
from django.contrib.auth.models import User
from utils.search.search import add_all_sounds_to_solr
from django.contrib.sites.models import Site
from utils.pagination import paginate
from django.core.urlresolvers import reverse
from utils.nginxsendfile import sendfile
import yaml
from utils.similarity_utilities import get_similar_sounds
from api.api_utils import auth, ReturnError

logger = logging.getLogger("api")

# UTILITY FUNCTIONS

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

def get_user_sounds_api_url(username):
    return prepend_base(reverse('api-user-sounds', args=[username]))

def get_user_packs_api_url(username):
    return prepend_base(reverse('api-user-packs', args=[username]))

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
        d['geotag'] = [sound.geotag.lat,sound._geotag_cache.lon]
    except:
        pass
    d['user'] = prepare_minimal_user(sound.user)
    d['tags'] = get_tags(sound)
    d.update(get_sound_links(sound))
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

def prepare_collection_sound(sound, include_user=True):
    d = {}
    for field in ["duration", "type", "original_filename", "id"]:
        d[field] = getattr(sound, field)
    if include_user:
        d['user'] = prepare_minimal_user(sound.user)
    d['tags'] = get_tags(sound)
    d.update(get_sound_links(sound))
    return d

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
    return d

def prepare_single_pack(pack, include_user=True):
    d = {}
    for field in ["name", "num_downloads", "created"]:
        d[field] = getattr(pack, field)
    user = User.objects.get(id=pack.user_id)
    if include_user:
        d['user'] = prepare_minimal_user(user)
    d['ref'] = get_pack_api_url(pack.id)
    d['url'] = get_pack_web_url(user.username, pack.id)
    d['sounds'] = get_pack_sounds_api_url(pack.id)
    return d


def find_api_option(cleaned_sort):
    for t in SEARCH_SORT_OPTIONS_API:
        if t[1] == cleaned_sort:
            return t[0]
    return None

def add_request_id(request,result):
    if request.GET.get('request_id', '')!='':
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
    curl:           curl http://www.freesound.org/api/search/?q=hoelahoep
    '''

    @auth()
    def read(self, request):

        form = SoundSearchForm(SEARCH_SORT_OPTIONS_API, request.GET)
        if not form.is_valid():
            resp = rc.BAD_REQUEST
            resp.content = form.errors
            return resp

        cd = form.cleaned_data
        #return cd

        solr = Solr(settings.SOLR_URL)

        query = search_prepare_query(cd['q'],
                                     cd['f'],
                                     search_prepare_sort(cd['s'], SEARCH_SORT_OPTIONS_API),
                                     cd['p'],
                                     settings.SOUNDS_PER_API_RESPONSE)

        try:
            results = SolrResponseInterpreter(solr.select(unicode(query)))
            paginator = SolrResponseInterpreterPaginator(results, settings.SOUNDS_PER_API_RESPONSE)
            page = paginator.page(form.cleaned_data['p'])
            sounds = []
            bad_results = 0
            for object in page['object_list'] :
                try:
                    sounds.append( prepare_collection_sound(Sound.objects.select_related('user').get(id=object['id'])) )
                except: # This will happen if there are synchronization errors between solr index and the database. In that case sounds are ommited and both num_results and results per page might become inacurate
                    pass
            result = {'sounds': sounds, 'num_results': paginator.count - bad_results, 'num_pages': paginator.num_pages}

            # construct previous and next urls
            if page['has_other_pages']:
                if page['has_previous']:
                    result['previous'] = self.__construct_pagination_link(cd['q'],
                                                                          page['previous_page_number'],
                                                                          cd['f'],
                                                                          find_api_option(cd['s']))
                if page['has_next']:
                    result['next'] = self.__construct_pagination_link(cd['q'],
                                                                      page['next_page_number'],
                                                                      cd['f'],
                                                                      find_api_option(cd['s']))
            add_request_id(request,result)
            return result

        except SolrException, e:
            error = "search_query %s filter_query %s sort %s error %s" \
                        % (cd['s'], cd['f'], cd['s'], e)
            raise ReturnError(500, "SearchError", {"explanation": error})


    def __construct_pagination_link(self, q, p, f, s):
        return prepend_base(reverse('api-search')+'?q=%s&p=%s&f=%s&s=%s' % (q,p,f,s))


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

        # DISABLED (FOR THE MOMENT WE DON'T UPDATE DOWNLOADS TABLE THROUGH API)
        #Download.objects.get_or_create(user=request.user, sound=sound, interface='A')

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
            sound = Sound.objects.get(id=sound_id, moderation_state="OK", processing_state="OK")
            #TODO: similarity_state="OK"
            #TODO: this filter has to be added again, but first the db has to be updated

        except Sound.DoesNotExist: #@UndefinedVariable
            raise ReturnError(404, "NotFound", {"explanation": "Sound with id %s does not exist." % sound_id})

        similar_sounds = get_similar_sounds(sound,request.GET.get('preset', settings.DEFAULT_SIMILARITY_PRESET), int(request.GET.get('num_results', settings.SOUNDS_PER_PAGE)) )

        sounds = []
        for similar_sound in similar_sounds :
            sound = prepare_collection_sound(Sound.objects.select_related('user').get(id=similar_sound[0]))
            sound['distance'] = similar_sound[1]
            sounds.append( sound )

        result = {'sounds': sounds, 'num_results': len(similar_sounds)}

        add_request_id(request,result)
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

        result = prepare_single_sound_analysis(sound,request,filter)

        add_request_id(request,result)
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
        return result

class UserSoundsHandler(BaseHandler):
    '''
    api endpoint:   /people/<username>/sounds
    '''
    allowed_methods = ('GET',)

    '''
    input:          p
    output:         #user_sounds#
    curl:           curl http://www.freesound.org/api/people/vincent_akkermans/sounds?p=5
    '''

    @auth()
    def read(self, request, username):
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            raise ReturnError(404, "NotFound", {"explanation": "User (%s) does not exist." % username})

        paginator = paginate(request, Sound.public.filter(user=user), settings.SOUNDS_PER_API_RESPONSE, 'p')
        page = paginator['page']
        sounds = [prepare_collection_sound(sound, include_user=False) for sound in page.object_list]
        result = {'sounds': sounds,  'num_results': paginator['paginator'].count, 'num_pages': paginator['paginator'].num_pages}

        if page.has_other_pages():
            if page.has_previous():
                result['previous'] = self.__construct_pagination_link(username, page.previous_page_number())
            if page.has_next():
                result['next'] = self.__construct_pagination_link(username, page.next_page_number())

        add_request_id(request,result)
        return result

    #TODO: auth() ?
    def __construct_pagination_link(self, u, p):
        return get_user_sounds_api_url(u)+'?p=%s' % p

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
        return result

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

        result = prepare_single_pack(pack)

        add_request_id(request,result)
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

        paginator = paginate(request, Sound.objects.filter(pack=pack.id), settings.SOUNDS_PER_API_RESPONSE, 'p')
        page = paginator['page']
        sounds = [prepare_collection_sound(sound, include_user=False) for sound in page.object_list]
        result = {'sounds': sounds, 'num_results': paginator['paginator'].count, 'num_pages': paginator['paginator'].num_pages}

        if page.has_other_pages():
            if page.has_previous():
                result['previous'] = self.__construct_pagination_link(pack_id, page.previous_page_number())
            if page.has_next():
                result['next'] = self.__construct_pagination_link(pack_id, page.next_page_number())

        add_request_id(request,result)
        return result

    def __construct_pagination_link(self, pack_id, p):
        return get_pack_sounds_api_url(pack_id)+'?p=%s' % p


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
