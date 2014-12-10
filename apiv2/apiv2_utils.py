# -*- coding: utf-8 -*-

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

from provider.views import OAuthError
from provider.scope import to_names, to_int
from provider.oauth2.views import AccessTokenView as DjangoRestFrameworkAccessTokenView, Authorize as DjangoOauth2ProviderAuthorize, Capture as DjangoOauth2ProviderCapture, Redirect as DjangoOauth2ProviderRedirect
from provider.oauth2.forms import PasswordGrantForm
from provider.oauth2.models import RefreshToken, AccessToken
from rest_framework.generics import GenericAPIView as RestFrameworkGenericAPIView, ListAPIView as RestFrameworkListAPIView, RetrieveAPIView as RestFrameworkRetrieveAPIView
from apiv2.authentication import OAuth2Authentication, TokenAuthentication, SessionAuthentication
import combined_search_strategies
from sounds.models import Sound, Pack, License
from utils.audioprocessing import get_sound_type
from geotags.models import GeoTag
from utils.filesystem import md5file
from utils.text import slugify
from exceptions import *
from examples import examples
import shutil
from django.conf import settings
import os
from utils.similarity_utilities import get_sounds_descriptors
from utils.search.solr import Solr, SolrException, SolrResponseInterpreter
from search.views import search_prepare_query
from utils.similarity_utilities import api_search as similarity_api_search
from similarity.client import SimilarityException
from urllib import unquote, quote
from django.http import HttpResponseRedirect, QueryDict
from django.utils.translation import ugettext as _
from django.contrib.sites.models import Site
from django.core.urlresolvers import resolve, reverse
import urlparse
from utils.cache import invalidate_template_cache
from django.contrib.auth.models import Group
from tickets.models import Ticket, Queue, LinkedContent, TicketComment
from tickets import TICKET_SOURCE_NEW_SOUND, TICKET_STATUS_NEW
import logging

logger_error = logging.getLogger("api_errors")


############################
# Authentication util tweaks
############################


class AccessTokenView(DjangoRestFrameworkAccessTokenView):

    '''
    We override only a function of the AccessTokenView class in order to be able to set different
    allowed grant types per API client and to resctrict scopes on a client basis.
    '''

    def get_password_grant(self, request, data, client):
        if not client.apiv2_client.allow_oauth_passoword_grant:
            raise OAuthError({'error': 'unsupported_grant_type'})

        form = PasswordGrantForm(data, client=client)
        if not form.is_valid():
            raise OAuthError(form.errors)
        return form.cleaned_data

    def get_access_token(self, request, user, scope, client):
        # If previous access tokens exist, delete them
        at = AccessToken.objects.filter(user=user, client=client)
        for ati in at:
            ati.delete()

        # Create a new access token
        at = self.create_access_token(request, user, scope, client)
        self.create_refresh_token(request, user, scope, at, client)
        return at

    def refresh_token(self, request, data, client):
        """
        Handle ``grant_type=refresh_token`` requests as defined in :draft:`6`.
        We overwrite this function so that old access tokens are deleted when refreshed. Otherwise multiple access tokens
        can be created, leading to errors.
        """
        rt = self.get_refresh_token_grant(request, data, client)

        #self.invalidate_refresh_token(rt)
        #self.invalidate_access_token(rt.access_token)
        scope = rt.access_token.scope
        rt.access_token.delete()

        at = self.create_access_token(request, rt.user, scope, client)
        rt.delete()
        rt = self.create_refresh_token(request, at.user, at.scope, at, client)

        return self.access_token_response(at)

    def create_access_token(self, request, user, scope, client):

        # Use client scope
        client_scope = client.apiv2_client.get_scope_display()
        #allowed_scopes = [requested_scope for requested_scope in to_names(scope) if requested_scope in client_scope]

        return AccessToken.objects.create(
            user=user,
            client=client,
            scope=to_int(*client_scope.split('+'))
        )

    def create_refresh_token(self, request, user, scope, access_token, client):

        return RefreshToken.objects.create(
            user=user,
            access_token=access_token,
            client=client
        )


class Capture(DjangoOauth2ProviderCapture):
    def get_redirect_url(self, request):
        return prepend_base(reverse('oauth2:authorize') + '/?original_path=%s' % quote(request.get_full_path()), use_https=not settings.DEBUG, dynamic_resolve=False)


class Authorize(DjangoOauth2ProviderAuthorize):
    if settings.USE_MINIMAL_TEMPLATES_FOR_OAUTH:
        template_name = 'api/minimal_authorize_app.html'
    else:
        template_name = 'api/authorize_app.html'

    def handle(self, request, post_data=None):
        data = self.get_data(request)
        original_path = quote(request.GET.get('original_path', ''))

        if data is None:
            return self.error_response(request, {
                'error': 'expired_authorization',
                'error_description': _('Authorization session has expired.')})

        try:
            client, data = self._validate_client(request, data)
        except OAuthError, e:
            if 'redirect_uri' in e.message:
                return self.error_response(request, {'error': 'The redirect_uri request parameter does not match the redirect_uri of ApiV2 client.'}, status=400)
            return self.error_response(request, e.args[0], status=400)

        # Check if request user already has validated access token for client
        has_valid_token = False
        try:
            if AccessToken.objects.filter(user=request.user, client=client).count():
                has_valid_token = True
        except:
            pass

        if not has_valid_token:
            # If user has no valid token display the authorization form as normal
            authorization_form = self.get_authorization_form(request, client, post_data, data)

            if not authorization_form.is_bound or not authorization_form.is_valid():
                return self.render_to_response({
                    'client': client,
                    'form': authorization_form,
                    'oauth_data': data,
                    'original_path': original_path, })
        else:
            # If user has a valid token fill the authorization form with a newly created grant and continue
            post_data = {u'authorize': [u'Authorize!']}
            authorization_form = self.get_authorization_form(request, client, post_data, data)
            if not authorization_form.is_valid():
                return self.render_to_response({
                    'client': client,
                    'form': authorization_form,
                    'oauth_data': data,
                    'original_path': original_path, })

        code = self.save_authorization(request, client, authorization_form, data)

        self.cache_data(request, data)
        self.cache_data(request, code, "code")
        self.cache_data(request, client, "client")

        return HttpResponseRedirect(prepend_base(self.get_redirect_url(request) + '/?original_path=%s' % original_path, use_https=not settings.DEBUG, dynamic_resolve=False))


class Redirect(DjangoOauth2ProviderRedirect):

    def get(self, request):

        data = self.get_data(request)
        code = self.get_data(request, "code")
        error = self.get_data(request, "error")
        client = self.get_data(request, "client")

        redirect_uri = client.redirect_uri # data.get('redirect_uri', None) or
        parsed = urlparse.urlparse(redirect_uri)
        query = QueryDict('', mutable=True)

        if 'state' in data:
            query['state'] = data['state']

        if error is not None:
            query.update(error)
        elif code is None:
            query['error'] = 'access_denied'
        else:
            query['code'] = code

        query['original_path'] = request.GET.get('original_path', '')

        parsed = parsed[:4] + (query.urlencode(), '')
        redirect_uri = urlparse.ParseResult(*parsed).geturl()
        self.clear_data(request)

        return HttpResponseRedirect(redirect_uri)


#############################
# Rest Framework custom views
#############################


class GenericAPIView(RestFrameworkGenericAPIView):
    throttling_rates_per_level = settings.APIV2_BASIC_THROTTLING_RATES_PER_LEVELS
    authentication_classes = (OAuth2Authentication, TokenAuthentication, SessionAuthentication)

    def initial(self, request, *args, **kwargs):
        super(GenericAPIView, self).initial(request, *args, **kwargs)

        # Get request information and store it as class variable
        self.end_user_ip = get_client_ip(request)
        self.auth_method_name, self.developer, self.user, self.client_id = get_authentication_details_form_request(request)

    def log_message(self, message):
        return '%s <%s> (%s)' % (message, request_parameters_info_for_log_message(self.request.QUERY_PARAMS), basic_request_info_for_log_message(self.auth_method_name, self.developer, self.user, self.client_id, self.end_user_ip))


class OauthRequiredAPIView(RestFrameworkGenericAPIView):
    throttling_rates_per_level = settings.APIV2_BASIC_THROTTLING_RATES_PER_LEVELS
    authentication_classes = (OAuth2Authentication, SessionAuthentication)

    def initial(self, request, *args, **kwargs):
        super(OauthRequiredAPIView, self).initial(request, *args, **kwargs)

        # Get request information and store it as class variable
        self.end_user_ip = get_client_ip(request)
        self.auth_method_name, self.developer, self.user, self.client_id = get_authentication_details_form_request(request)

        # Check if using https
        throw_exception_if_not_https(request)

    def log_message(self, message):
        return '%s <%s> (%s)' % (message, request_parameters_info_for_log_message(self.request.QUERY_PARAMS), basic_request_info_for_log_message(self.auth_method_name, self.developer, self.user, self.client_id, self.end_user_ip))


class DownloadAPIView(OauthRequiredAPIView):
    throttling_rates_per_level = settings.APIV2_BASIC_THROTTLING_RATES_PER_LEVELS


class WriteRequiredGenericAPIView(RestFrameworkGenericAPIView):
    throttling_rates_per_level = settings.APIV2_POST_THROTTLING_RATES_PER_LEVELS
    authentication_classes = (OAuth2Authentication, SessionAuthentication)

    def initial(self, request, *args, **kwargs):
        super(WriteRequiredGenericAPIView, self).initial(request, *args, **kwargs)

        # Get request informationa dn store it as class variable
        self.end_user_ip = get_client_ip(request)
        self.auth_method_name, self.developer, self.user, self.client_id = get_authentication_details_form_request(request)

        # Check if using https
        throw_exception_if_not_https(request)

        # Check if client has write permissions
        if self.auth_method_name == "OAuth2":
            if "write" not in request.auth.client.apiv2_client.get_scope_display():
                raise UnauthorizedException(resource=self)

    def log_message(self, message):
        return '%s <%s> (%s)' % (message, request_parameters_info_for_log_message(self.request.QUERY_PARAMS), basic_request_info_for_log_message(self.auth_method_name, self.developer, self.user, self.client_id, self.end_user_ip))


class ListAPIView(RestFrameworkListAPIView):
    throttling_rates_per_level = settings.APIV2_BASIC_THROTTLING_RATES_PER_LEVELS
    authentication_classes = (OAuth2Authentication, TokenAuthentication, SessionAuthentication)

    def initial(self, request, *args, **kwargs):
        super(ListAPIView, self).initial(request, *args, **kwargs)

        # Get request information and store it as class variable
        self.end_user_ip = get_client_ip(request)
        self.auth_method_name, self.developer, self.user, self.client_id = get_authentication_details_form_request(request)

    def log_message(self, message):
        return '%s <%s> (%s)' % (message, request_parameters_info_for_log_message(self.request.QUERY_PARAMS), basic_request_info_for_log_message(self.auth_method_name, self.developer, self.user, self.client_id, self.end_user_ip))


class RetrieveAPIView(RestFrameworkRetrieveAPIView):
    throttling_rates_per_level = settings.APIV2_BASIC_THROTTLING_RATES_PER_LEVELS
    authentication_classes = (OAuth2Authentication, TokenAuthentication, SessionAuthentication)

    def initial(self, request, *args, **kwargs):
        super(RetrieveAPIView, self).initial(request, *args, **kwargs)

        # Get request information and store it as class variable
        self.end_user_ip = get_client_ip(request)
        self.auth_method_name, self.developer, self.user, self.client_id = get_authentication_details_form_request(request)

    def log_message(self, message):
        return '%s <%s> (%s)' % (message, request_parameters_info_for_log_message(self.request.QUERY_PARAMS), basic_request_info_for_log_message(self.auth_method_name, self.developer, self.user, self.client_id, self.end_user_ip))


##################
# Search utilities
##################

def api_search(search_form, target_file=None, extra_parameters=False, merging_strategy='merge_optimized', resource=None):

    if search_form.cleaned_data['query']  == None and search_form.cleaned_data['filter'] == None and not search_form.cleaned_data['descriptors_filter'] and not search_form.cleaned_data['target'] and not target_file:
        # No input data for search, return empty results
        return [], 0, None, None, None, None, None

    if search_form.cleaned_data['query'] == None and search_form.cleaned_data['filter'] == None:
        # Standard content-based search
        try:
            results, count, note = similarity_api_search(target=search_form.cleaned_data['target'],
                                                         filter=search_form.cleaned_data['descriptors_filter'],
                                                         num_results=search_form.cleaned_data['page_size'],
                                                         offset=(search_form.cleaned_data['page'] - 1) * search_form.cleaned_data['page_size'],
                                                         target_file=target_file)

            gaia_ids = [result[0] for result in results]
            distance_to_target_data = None
            if search_form.cleaned_data['target'] or target_file:
                # Save sound distance to target into view class so it can be accessed by the serializer
                # We only do that when a target is specified (otherwise there is no meaningful distance value)
                distance_to_target_data = dict(results)

            gaia_count = count
            return gaia_ids, gaia_count, distance_to_target_data, None, note, None, None
        except SimilarityException, e:
            if e.status_code == 500:
                raise ServerErrorException(msg=e.message, resource=resource)
            elif e.status_code == 400:
                raise BadRequestException(msg=e.message, resource=resource)
            elif e.status_code == 404:
                raise NotFoundException(msg=e.message, resource=resource)
            else:
                raise ServerErrorException(msg='Similarity server error: %s' % e.message, resource=resource)
        except Exception, e:
            raise ServerErrorException(msg='The similarity server could not be reached or some unexpected error occurred.', resource=resource)


    elif not search_form.cleaned_data['descriptors_filter'] and not search_form.cleaned_data['target'] and not target_file:
        # Standard text-based search
        try:
            solr = Solr(settings.SOLR_URL)
            query = search_prepare_query(unquote(search_form.cleaned_data['query'] or ""),
                                         unquote(search_form.cleaned_data['filter'] or ""),
                                         search_form.cleaned_data['sort'],
                                         search_form.cleaned_data['page'],
                                         search_form.cleaned_data['page_size'],
                                         grouping=search_form.cleaned_data['group_by_pack'],
                                         include_facets=False)

            result = SolrResponseInterpreter(solr.select(unicode(query)))
            solr_ids = [element['id'] for element in result.docs]
            solr_count = result.num_found

            more_from_pack_data = None
            if search_form.cleaned_data['group_by_pack']:
                # If grouping option is on, store grouping info in a dictionary that we can add when serializing sounds
                more_from_pack_data = dict([(int(element['id']), [element['more_from_pack'], element['pack_id'], element['pack_name']]) for element in result.docs])

            return solr_ids, solr_count, None, more_from_pack_data, None, None, None

        except SolrException, e:
            if search_form.cleaned_data['filter'] != None:
                raise BadRequestException(msg='Search server error: %s (please check that your filter syntax and field names are correct)' % e.message, resource=resource)
            raise BadRequestException(msg='Search server error: %s' % e.message, resource=resource)
        except Exception, e:
            raise ServerErrorException(msg='The search server could not be reached or some unexpected error occurred.', resource=resource)

    else:
        # Combined search (there is at least one of query/filter and one of descriptors_filter/target)
        # Strategies are implemented in 'combined_search_strategies'
        strategy = getattr(combined_search_strategies, merging_strategy)
        return strategy(search_form, target_file=target_file, extra_parameters=extra_parameters)


###############
# OTHER UTILS
###############

# General utils
###############

def build_request_info_string_for_error_logging(request):
    auth_method_name, developer, user, client_id = get_authentication_details_form_request(request)
    end_user_ip = get_client_ip(request)
    request_info = basic_request_info_for_log_message(auth_method_name, developer, user, client_id, end_user_ip)
    return request_info

def throw_exception_if_not_https(request):
    if not settings.DEBUG:
        if not request.is_secure():
            request_info = build_request_info_string_for_error_logging(request)
            raise RequiresHttpsException(request_info=request_info)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = '-' #request.META.get('REMOTE_ADDR')
    return ip

def prepend_base(rel, dynamic_resolve=True, use_https=False, request_is_secure=False):

    if request_is_secure:
        use_https = True
        dynamic_resolve = False  # don't need to dynamic resolve is request is https

    if dynamic_resolve:
        try:
            url_name = resolve(rel.replace('<sound_id>', '1').replace('<username', 'name').replace('<pack_id>', '1').replace('<category_id>', '1')).url_name
            if url_name in settings.APIV2_RESOURCES_REQUIRING_HTTPS:
                use_https = True
        except Exception, e:
            pass

    if use_https:
        return "https://%s%s" % (Site.objects.get_current().domain, rel)
    else:
        return "http://%s%s" % (Site.objects.get_current().domain, rel)

def get_authentication_details_form_request(request):
    auth_method_name = None
    user = None
    developer = None
    client_id = None

    if request.successful_authenticator:
        auth_method_name = request.successful_authenticator.authentication_method_name
        if auth_method_name == "OAuth2":
            user = request.user
            developer = request.auth.client.user
            client_id = request.auth.client.apiv2_client.client_id
        elif auth_method_name == "Token":
            user = None
            developer = request.auth.user
            client_id = request.auth.client_id
        elif auth_method_name == "Session":
            user = request.user
            developer = None
            client_id = None

    return auth_method_name, developer, user, client_id


def basic_request_info_for_log_message(auth_method_name, developer, user, client_id, ip):
    return 'ApiV2 Auth:%s Dev:%s User:%s Client:%s Ip:%s' % (auth_method_name, developer, user, str(client_id), ip)


def request_parameters_info_for_log_message(get_parameters):
    return ','.join(['%s=%s' % (key, value) for key, value in get_parameters.items()])


class ApiSearchPaginator(object):
    def __init__(self, results, count, num_per_page):
        self.num_per_page = num_per_page
        self.count = count
        self.num_pages = count / num_per_page + int(count % num_per_page != 0)
        self.page_range = range(1, self.num_pages + 1)
        self.results = results

    def page(self, page_num):
        object_list = self.results
        has_next = page_num < self.num_pages
        has_previous = page_num > 1 and page_num <= self.num_pages
        has_other_pages = has_next or has_previous
        next_page_number = page_num + 1
        previous_page_number = page_num - 1
        return locals()


# Docs examples utils
#####################

def get_formatted_examples_for_view(view_name, url_name, max=10):
    try:
        data = examples[view_name]
    except:
        #print 'Could not find examples for view %s' % view_name
        return ''

    count = 0
    output = 'Some quick examples:<div class="request-info" style="clear: both"><pre class="prettyprint">'

    for description, elements in data:
        for element in elements:
            if count >= max:
                break

            if element[0:5] == 'apiv2':
                if url_name in settings.APIV2_RESOURCES_REQUIRING_HTTPS:
                    url = prepend_base('/' + element, dynamic_resolve=False, use_https=True)
                else:
                    url = prepend_base('/' + element, dynamic_resolve=False, use_https=False)
                output += '<span class="pln"><a href="%s">%s</a></span><br>' % (url, url)
            else:
                # This is only apiv2 oauth examples
                url = prepend_base('', dynamic_resolve=False, use_https=True)
                output += '<span class="pln">%s</span><br>' % (element % url)
            count += 1

    output += '</pre></div>'

    return output

# Similarity utils
##################

def get_analysis_data_for_queryset_or_sound_ids(view, queryset=None, sound_ids=[]):
    # Get analysis data for all requested sounds and save it to a class variable so the serializer can access it and
    # we only need one request to the similarity service

    analysis_data_required = 'analysis' in view.request.QUERY_PARAMS.get('fields', '').split(',')
    if analysis_data_required:
        # Get ids of the particular sounds we need
        if queryset:
            paginated_queryset = view.paginate_queryset(queryset)
            ids = [int(sound.id) for sound in paginated_queryset.object_list]
        else:
            ids = [int(sid) for sid in sound_ids]

        # Get descriptor values for the required ids
        # Required descriptors are indicated with the parameter 'descriptors'. If 'descriptors' is empty, we return nothing
        descriptors = view.request.QUERY_PARAMS.get('descriptors', [])
        view.sound_analysis_data = {}
        if descriptors:
            try:
                view.sound_analysis_data = get_sounds_descriptors(ids,
                                                                  descriptors.split(','),
                                                                  view.request.QUERY_PARAMS.get('normalized', '0') == '1',
                                                                  only_leaf_descriptors=True)
            except:
                pass
        else:
            for id in ids:
                view.sound_analysis_data[str(id)] = 'No descriptors specified. You should indicate which descriptors you want with the \'descriptors\' request parameter.'


# Upload handler utils
######################

def create_sound_object(user, original_sound_fields, resource=None, apiv2_client=None):
    '''
    This function is used by the upload handler to create a sound object with the information provided through post
    parameters.
    '''

    # 1 prepare some variable names
    sound_fields = dict()
    for key, item in original_sound_fields.items():
        sound_fields[key] = item

    filename = sound_fields['upload_filename']
    if not 'name' in sound_fields:
        sound_fields['name'] = filename
    else:
        if not sound_fields['name']:
            sound_fields['name'] = filename

    directory = os.path.join(settings.UPLOADS_PATH, str(user.id))
    dest_path = os.path.join(directory, filename)

    # 2 make sound object
    sound = Sound()
    sound.user = user
    sound.original_filename = sound_fields['name']
    sound.original_path = dest_path
    sound.filesize = os.path.getsize(sound.original_path)
    sound.type = get_sound_type(sound.original_path)
    license = License.objects.get(name=sound_fields['license'])
    sound.license = license

    # 3 md5, check
    try:
        sound.md5 = md5file(sound.original_path)
    except IOError:
        if settings.DEBUG:
            msg = "Md5 could not be computed."
        else:
            msg = "Server error."
        raise ServerErrorException(msg=msg, resource=resource)

    sound_already_exists = Sound.objects.filter(md5=sound.md5).exists()
    if sound_already_exists:
        os.remove(sound.original_path)
        raise OtherException("Sound could not be created because the uploaded file is already part of freesound.", resource=resource)

    # 4 save
    sound.save()

    # 5 move to new path
    orig = os.path.splitext(os.path.basename(sound.original_filename))[0]  # WATCH OUT!
    sound.base_filename_slug = "%d__%s__%s" % (sound.id, slugify(sound.user.username), slugify(orig))
    new_original_path = sound.locations("path")
    if sound.original_path != new_original_path:
        try:
            os.makedirs(os.path.dirname(new_original_path))
        except OSError:
            pass
        try:
            shutil.move(sound.original_path, new_original_path)
        except IOError, e:
            if settings.DEBUG:
                msg = "File could not be copied to the correct destination."
            else:
                msg = "Server error."
            raise ServerErrorException(msg=msg, resource=resource)
        sound.original_path = new_original_path
        sound.save()

    # 6 create pack if it does not exist
    if 'pack' in sound_fields:
        if sound_fields['pack']:
            if Pack.objects.filter(name=sound_fields['pack'], user=user).exists():
                p = Pack.objects.get(name=sound_fields['pack'], user=user)
            else:
                p, created = Pack.objects.get_or_create(user=user, name=sound_fields['pack'])
            sound.pack = p

    # 7 create geotag objects
    # format: lat#lon#zoom
    if 'geotag' in sound_fields:
        if sound_fields['geotag']:
            lat, lon, zoom = sound_fields['geotag'].split(',')
            geotag = GeoTag(user=user,
                lat=float(lat),
                lon=float(lon),
                zoom=int(zoom))
            geotag.save()
            sound.geotag = geotag

    # 8 set description, tags
    sound.description = sound_fields['description']
    sound.set_tags(sound_fields['tags'])
    #sound.set_tags([t.lower() for t in sound_fields['tags'].split(" ") if t])

    # 8.5 set uploaded apiv2 client
    sound.uploaded_with_apiv2_client = apiv2_client

    # 9 save!
    sound.save()

    # 10 create moderation tickets if needed
    if user.profile.is_whitelisted:
        sound.moderation_state = 'OK'
        sound.save()
    else:
        # create moderation ticket!
        ticket = Ticket()
        ticket.title = 'Moderate sound %s' % sound.original_filename
        ticket.source = TICKET_SOURCE_NEW_SOUND
        ticket.status = TICKET_STATUS_NEW
        ticket.queue = Queue.objects.get(name='sound moderation')
        ticket.sender = user
        lc = LinkedContent()
        lc.content_object = sound
        lc.save()
        ticket.content = lc
        ticket.save()
        tc = TicketComment()
        tc.sender = user
        tc.text = "I've uploaded %s. Please moderate!" % sound.original_filename
        tc.ticket = ticket
        tc.save()

        invalidate_template_cache("user_header", ticket.sender.id)
        moderators = Group.objects.get(name='moderators').user_set.all()
        for moderator in moderators:
            invalidate_template_cache("user_header", moderator.id)

    # 11 proces
    try:
        sound.compute_crc()
    except:
        pass

    try:
        sound.process()
    except Exception, e:
        # Log that sound could not be processed, but do not throw any exception
        request_info = basic_request_info_for_log_message(resource.auth_method_name, resource.developer, resource.user, resource.client_id, resource.end_user_ip)
        msg = str(e)
        logger.error('<%i API uploaded sound could not be processed> %s (%s)' % (status.HTTP_500_INTERNAL_SERVER_ERROR, msg, request_info))
        pass

    return sound