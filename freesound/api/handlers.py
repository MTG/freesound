from django.conf import settings
from piston.handler import BaseHandler
from piston.utils import rc
from search.forms import SoundSearchForm, SEARCH_SORT_OPTIONS_API
from search.views import search_prepare_sort, search_prepare_query
from sounds.models import Sound, Pack
from utils.search.solr import Solr, SolrException, SolrResponseInterpreter, SolrResponseInterpreterPaginator
import logging, os
from django.core.servers.basehttp import FileWrapper
from django.http import HttpResponse
from django.contrib.auth.models import User
from utils.search.search import add_all_sounds_to_solr
from django.contrib.sites.models import Site
from utils.pagination import paginate
from django.core.urlresolvers import reverse

logger = logging.getLogger("api")

'''
N.B.:
- #x# and %x% aliases are defined in the Freesound API v1 google doc.
- curl examples do not include authentication

TODO:
- check serving of files

LATER:
- throttling
- download updates
'''

# UTILITY FUNCTIONS

def prepend_base(rel):
    return "http://%s%s" % (Site.objects.get_current().domain, rel)

def get_sound_api_url(id):
    return prepend_base(reverse('api-single-sound', args=[id]))

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
    d = {'ref': ref,
         'url': get_sound_web_url(sound.user.username, sound.id),
         'serve': ref+'/serve',
         'preview': ref+'/preview',
         'waveform_m': prepare_image_link(sound.paths()['waveform_path_m']),
         'waveform_l': prepare_image_link(sound.paths()['waveform_path_l']),
         'spectral_m': prepare_image_link(sound.paths()['spectral_path_m']),
         'spectral_l': prepare_image_link(sound.paths()['spectral_path_l']),}
    if sound.pack_id:
        d['pack'] = get_pack_api_url(sound.pack_id)
    return d

def prepare_image_link(p):
    if settings.DATA_URL.startswith('/'):
        return prepend_base(settings.DATA_URL)+p
    else:
        return settings.DATA_URL + p 

def prepare_minimal_user(user):
    return {'username': user.username,
            'ref': get_user_api_url(user.username),
            'url': get_user_web_url(user.username),}

def prepare_single_sound(sound):
    d = {}
    for field in ["num_downloads", "channels", "duration", "samplerate", "samplerate", \
                  "id", "num_comments", "num_ratings", "filesize", "base_filename_slug", \
                  "type", "description", "original_path", "bitdepth", "bitrate",  "created", \
                  "avg_rating", "original_filename"]:
        d[field] = getattr(sound, field)
    try:
        d['license'] = sound.license.name
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

def get_tags(sound):
    return [tagged.tag.name for tagged in sound.tags.select_related("tag").all()]

def prepare_collection_sound(sound, include_user=True):
    d = {}
    for field in ["duration", "base_filename_slug", "type", "original_filename"]:
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
    for field in ["description", "name", "num_downloads", "created"]:
        d[field] = getattr(pack, field)
    user = User.objects.get(id=pack.user_id)
    if include_user:
        d['user'] = prepare_minimal_user(user)
    d['ref'] = get_pack_api_url(pack.id)
    d['url'] = get_pack_web_url(user.username, pack.id)
    d['sounds'] = get_pack_sounds_api_url(pack.id)
    return d

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
    def read(self, request):
        form = SoundSearchForm(SEARCH_SORT_OPTIONS_API, request.GET)
        if not form.is_valid():
            resp = rc.BAD_REQUEST
            resp.content = form.errors
            return resp
        
        cd = form.cleaned_data

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
            sounds = [prepare_collection_sound(Sound.objects.select_related('user').get(id=object['id'])) \
                      for object in page['object_list']]
            result = {'sounds': sounds}
            print result
            # construct previous and next urls
            if page['has_other_pages']:
                if page['has_previous']:
                    result['previous'] = self.__construct_pagination_link(cd['q'], 
                                                                          page['previous_page_number'], 
                                                                          cd['f'], 
                                                                          cd['s'])
                if page['has_next']:
                    result['next'] = self.__construct_pagination_link(cd['q'], 
                                                                      page['next_page_number'], 
                                                                      cd['f'], 
                                                                      cd['s'])
            return result
        except SolrException, e:
            error = "search error: search_query %s filter_query %s sort %s error %s" \
                        % (cd['s'], cd['f'], cd['s'], e)
            logger.warning(error)
            resp = rc.ALL_OK
            resp.status_code = 500
            resp.content = error
            return resp
    
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
    def read(self, request, sound_id):
        
        try:
            sound = Sound.objects.select_related('geotag', 'user', 'license', 'tags').get(id=sound_id, moderation_state="OK", processing_state="OK")
        except Sound.DoesNotExist: #@UndefinedVariable
            resp = rc.NOT_FOUND
            resp = 'There is no sound with id %s' % sound_id
            return resp
        return prepare_single_sound(sound)
        
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
    def read(self, request, sound_id, file_or_preview):
        if not file_or_preview in ['serve', 'preview']:
            resp = rc.NOT_FOUND
            return resp
        try:
            sound = Sound.objects.get(id=sound_id, moderation_state="OK", processing_state="OK")
        except Sound.DoesNotExist: #@UndefinedVariable
            resp = rc.NOT_FOUND
            resp = 'There is no sound with id %s' % sound_id
            return resp
        sound_path = sound.paths()["sound_path"] if file_or_preview == 'serve' else sound.paths()['preview_path']
        if settings.DEBUG:
            file_path = os.path.join(settings.DATA_PATH, sound_path)
            wrapper = FileWrapper(file(file_path, "rb"))
            response = HttpResponse(wrapper, content_type='application/octet-stream')
            response['Content-Length'] = os.path.getsize(file_path)
            return response
        else:
            response = HttpResponse()
            response['Content-Type']="application/octet-stream"
            response['X-Accel-Redirect'] = os.path.join("downloads/", sound_path)
            return response

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
    def read(self, request, username):
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            resp = rc.NOT_FOUND
            resp.content = 'This user (%s) does not exist.' % username
            return resp
        return prepare_single_user(user)
    
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
    def read(self, request, username):
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            resp = rc.NOT_FOUND
            resp.content = 'This user (%s) does not exist.' % username
            return resp
        page = paginate(request, Sound.public.filter(user=user), settings.SOUNDS_PER_API_RESPONSE, 'p')['page']
        sounds = [prepare_collection_sound(sound, include_user=False) for sound in page.object_list]
        result = {'sounds': sounds}
        if page.has_other_pages():
            if page.has_previous():
                result['previous'] = self.__construct_pagination_link(username, page.previous_page_number())
            if page.has_next():
                result['next'] = self.__construct_pagination_link(username, page.next_page_number())
        return result
    
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
    def read(self, request, username):
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            resp = rc.NOT_FOUND
            resp.content = 'This user (%s) does not exist.' % username
            return resp
        packs = [prepare_single_pack(pack, include_user=False) for pack in Pack.objects.filter(user=user)]
        return packs

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
    def read(self, request, pack_id):
        try:
            pack = Pack.objects.get(id=pack_id)
        except User.DoesNotExist:
            resp = rc.NOT_FOUND
            resp.content = 'There is no pack with this identifier (%s).' % pack_id
            return resp
        return prepare_single_pack(pack)

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
    def read(self, request, pack_id):
        try:
            pack = Pack.objects.get(id=pack_id)
        except User.DoesNotExist:
            resp = rc.NOT_FOUND
            resp.content = 'There is no pack with this identifier (%s).' % pack_id
            return resp
        page = paginate(request, Sound.objects.filter(pack=pack.id), settings.SOUNDS_PER_API_RESPONSE, 'p')['page']
        sounds = [prepare_collection_sound(sound, include_user=False) for sound in page.object_list]
        result = {'sounds': sounds}
        if page.has_other_pages():
            if page.has_previous():
                result['previous'] = self.__construct_pagination_link(pack_id, page.previous_page_number())
            if page.has_next():
                result['next'] = self.__construct_pagination_link(pack_id, page.next_page_number())
        return result
    
    def __construct_pagination_link(self, pack_id, p):
        return get_pack_sounds_api_url(pack_id)+'?p=%s' % p


# N.B. don't add this to a production environment!
class UpdateSolrHandler(BaseHandler):
    allowed_methods = ('GET',)
    
    def read(self, request):
        add_all_sounds_to_solr()
        return rc.ALL_OK
    