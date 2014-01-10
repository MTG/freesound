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
from provider.oauth2.views import AccessTokenView as DjangoRestFrameworkAccessTokenView, Authorize as DjangoOauth2ProviderAuthorize
from provider.oauth2.forms import PasswordGrantForm
from provider.oauth2.models import RefreshToken, AccessToken
from rest_framework.generics import GenericAPIView as RestFrameworkGenericAPIView, ListAPIView as RestFrameworkListAPIView, RetrieveAPIView as RestFrameworkRetrieveAPIView
from apiv2.authentication import OAuth2Authentication, TokenAuthentication, SessionAuthentication
from sounds.models import Sound, Pack, License
from freesound.utils.audioprocessing import get_sound_type
from geotags.models import GeoTag
from freesound.utils.filesystem import md5file
from freesound.utils.text import slugify
from exceptions import ServerErrorException, OtherException, UnauthorizedException, InvalidUrlException, NotFoundException
from examples import examples
import shutil
import settings
import os
from freesound.utils.similarity_utilities import get_sounds_descriptors
from freesound.utils.search.solr import Solr, SolrException, SolrResponseInterpreter
from search.views import search_prepare_query, search_prepare_sort
from apiv2.forms import SEARCH_SORT_OPTIONS_API
from freesound.utils.similarity_utilities import api_search as similarity_api_search
from similarity.client import SimilarityException
from urllib import unquote
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext as _
from django.contrib.sites.models import Site


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

        # Filter out requested scopes and only leave those allowed to the client
        client_scope = client.apiv2_client.get_scope_display()
        allowed_scopes = [requested_scope for requested_scope in to_names(scope) if requested_scope in client_scope]

        return AccessToken.objects.create(
            user=user,
            client=client,
            scope=to_int(*allowed_scopes)
        )

    def create_refresh_token(self, request, user, scope, access_token, client):

        return RefreshToken.objects.create(
            user=user,
            access_token=access_token,
            client=client
        )


class Authorize(DjangoOauth2ProviderAuthorize):
    if settings.USE_MINIMAL_TEMPLATES_FOR_OAUTH:
        template_name = 'api/minimal_authorize_app.html'
    else:
        template_name = 'api/authorize_app.html'

    def handle(self, request, post_data=None):
        data = self.get_data(request)

        if data is None:
            return self.error_response(request, {
                'error': 'expired_authorization',
                'error_description': _('Authorization session has expired.')})

        try:
            client, data = self._validate_client(request, data)
        except OAuthError, e:
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
                    'oauth_data': data, })
        else:
            # If user has a valid token fill the authorization form with a newly created grant and continue
            post_data = {u'authorize': [u'Authorize!']}
            authorization_form = self.get_authorization_form(request, client, post_data, data)
            if not authorization_form.is_valid():
                return self.render_to_response({
                    'client': client,
                    'form': authorization_form,
                    'oauth_data': data, })

        code = self.save_authorization(request, client, authorization_form, data)

        self.cache_data(request, data)
        self.cache_data(request, code, "code")
        self.cache_data(request, client, "client")

        return HttpResponseRedirect(self.get_redirect_url(request))


#############################
# Rest Framework custom views
#############################


class GenericAPIView(RestFrameworkGenericAPIView):
    authentication_classes = (OAuth2Authentication, TokenAuthentication, SessionAuthentication)

    def initial(self, request, *args, **kwargs):
        super(GenericAPIView, self).initial(request, *args, **kwargs)

        # Get request information and store it as class variable
        self.auth_method_name, self.developer, self.user, self.client_id = get_authentication_details_form_request(request)

    def log_message(self, message):
        return '%s <%s> (%s)' % (message, request_parameters_info_for_log_message(self.request.QUERY_PARAMS), basic_request_info_for_log_message(self.auth_method_name, self.developer, self.user, self.client_id))


class DownloadAPIView(RestFrameworkGenericAPIView):
    authentication_classes = (OAuth2Authentication, SessionAuthentication)

    def initial(self, request, *args, **kwargs):
        super(DownloadAPIView, self).initial(request, *args, **kwargs)

        # Get request information and store it as class variable
        self.auth_method_name, self.developer, self.user, self.client_id = get_authentication_details_form_request(request)

    def log_message(self, message):
        return '%s <%s> (%s)' % (message, request_parameters_info_for_log_message(self.request.QUERY_PARAMS), basic_request_info_for_log_message(self.auth_method_name, self.developer, self.user, self.client_id))

class WriteRequiredGenericAPIView(RestFrameworkGenericAPIView):
    authentication_classes = (OAuth2Authentication, SessionAuthentication)

    def initial(self, request, *args, **kwargs):
        super(WriteRequiredGenericAPIView, self).initial(request, *args, **kwargs)

        # Get request informationa dn store it as class variable
        self.auth_method_name, self.developer, self.user, self.client_id = get_authentication_details_form_request(request)

        # Check if client has write permissions
        if self.auth_method_name == "OAuth2":
            if "write" not in request.auth.client.apiv2_client.get_scope_display():
                raise UnauthorizedException

    def log_message(self, message):
        return '%s <%s> (%s)' % (message, request_parameters_info_for_log_message(self.request.QUERY_PARAMS), basic_request_info_for_log_message(self.auth_method_name, self.developer, self.user, self.client_id))


class ListAPIView(RestFrameworkListAPIView):
    authentication_classes = (OAuth2Authentication, TokenAuthentication, SessionAuthentication)

    def initial(self, request, *args, **kwargs):
        super(ListAPIView, self).initial(request, *args, **kwargs)

        # Get request information and store it as class variable
        self.auth_method_name, self.developer, self.user, self.client_id = get_authentication_details_form_request(request)

    def log_message(self, message):
        return '%s <%s> (%s)' % (message, request_parameters_info_for_log_message(self.request.QUERY_PARAMS), basic_request_info_for_log_message(self.auth_method_name, self.developer, self.user, self.client_id))


class RetrieveAPIView(RestFrameworkRetrieveAPIView):
    authentication_classes = (OAuth2Authentication, TokenAuthentication, SessionAuthentication)

    def initial(self, request, *args, **kwargs):
        super(RetrieveAPIView, self).initial(request, *args, **kwargs)

        # Get request information and store it as class variable
        self.auth_method_name, self.developer, self.user, self.client_id = get_authentication_details_form_request(request)

    def log_message(self, message):
        return '%s <%s> (%s)' % (message, request_parameters_info_for_log_message(self.request.QUERY_PARAMS), basic_request_info_for_log_message(self.auth_method_name, self.developer, self.user, self.client_id))


##################
# Search utilities
##################

def api_search(search_form, target_file=None):

    distance_to_target_data = None

    if not search_form.cleaned_data['query'] and not search_form.cleaned_data['filter'] and not search_form.cleaned_data['descriptors_filter'] and not search_form.cleaned_data['target'] and not target_file:
        # No input data for search, return empty results
        return [], 0, None, None, None

    if not search_form.cleaned_data['query'] and not search_form.cleaned_data['filter']:
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
            return gaia_ids, gaia_count, distance_to_target_data, None, note
        except SimilarityException, e:
            if e.status_code == 500:
                raise ServerErrorException(msg=e.message)
            elif e.status_code == 400:
                raise InvalidUrlException(msg=e.message)
            elif e.status_code == 404:
                raise NotFoundException(msg=e.message)
            else:
                raise ServerErrorException(msg=e.message)
        except Exception, e:
            if settings.DEBUG:
                raise ServerErrorException(msg=e.message)
            else:
                raise ServerErrorException()


    elif not search_form.cleaned_data['descriptors_filter'] and not search_form.cleaned_data['target'] and not target_file:
        # Standard text-based search
        try:
            solr = Solr(settings.SOLR_URL)
            query = search_prepare_query(unquote(search_form.cleaned_data['query']),
                                         unquote(search_form.cleaned_data['filter']),
                                         search_prepare_sort(search_form.cleaned_data['sort'], SEARCH_SORT_OPTIONS_API),
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

            return solr_ids, solr_count, None, more_from_pack_data, None

        except SolrException, e:
            raise InvalidUrlException(msg='Solr exception: %s' % e.message)
        except Exception, e:
            if settings.DEBUG:
                raise ServerErrorException(msg=e.message)
            else:
                raise ServerErrorException()

    else:
        # Combined search (there is at least one of query/filter and one of desriptors_filter/target)

        # Get solr results
        solr = Solr(settings.SOLR_URL)
        solr_ids = []
        solr_count = None
        more_from_pack_data = None
        if search_form.cleaned_data['group_by_pack']:
            more_from_pack_data = dict()
        PAGE_SIZE = 1000
        current_page = 1
        try:
            while len(solr_ids) < solr_count or solr_count == None:
                query = search_prepare_query(unquote(search_form.cleaned_data['query']),
                                             unquote(search_form.cleaned_data['filter']),
                                             search_prepare_sort(search_form.cleaned_data['sort'], SEARCH_SORT_OPTIONS_API),
                                             current_page,
                                             PAGE_SIZE,
                                             grouping=search_form.cleaned_data['group_by_pack'],
                                             include_facets=False,
                                             grouping_pack_limit=1000)  # We want to get all results in the same group so we can filter them out with content data and provide accurate 'more_from_pack' counts
                result = SolrResponseInterpreter(solr.select(unicode(query)))
                solr_ids += [element['id'] for element in result.docs]
                solr_count = result.num_found
                if search_form.cleaned_data['group_by_pack']:
                    # If grouping option is on, store grouping info in a dictionary that we can add when serializing sounds
                    more_from_pack_data.update(dict([(int(element['id']), [element['more_from_pack'], element['pack_id'], element['pack_name'], element['other_ids']]) for element in result.docs]))
                current_page += 1
        except SolrException, e:
            raise InvalidUrlException(msg='Solr exception: %s' % e.message)
        except Exception, e:
            if settings.DEBUG:
                raise ServerErrorException(msg=e.message)
            else:
                raise ServerErrorException()

        # Get gaia results
        try:
            results, count, note = similarity_api_search(target=search_form.cleaned_data['target'],
                                                         filter=search_form.cleaned_data['descriptors_filter'],
                                                         num_results=99999999,  # Return all sounds in one page
                                                         offset=0,
                                                         target_file=target_file)
            gaia_ids = [id[0] for id in results]
            distance_to_target_data = None
            if search_form.cleaned_data['target'] or target_file:
                # Save sound distance to target into view class so it can be accessed by the serializer
                # We only do that when a target is specified (otherwise there is no meaningful distance value)
                distance_to_target_data = dict(results)

            if search_form.cleaned_data['group_by_pack']:
                # If results were grouped by pack, we need to update the counts of the 'more_from_pack' property, as they do not
                # consider the gaia search result and will not be accurate.
                keys_to_remove = []
                for key, value in more_from_pack_data.items():
                    ids_from_pack_in_gaia_results = list(set(more_from_pack_data[key][3]).intersection(gaia_ids))
                    if ids_from_pack_in_gaia_results:
                        # Update more_from_pack_data values
                        more_from_pack_data[key][0] = len(ids_from_pack_in_gaia_results)
                        more_from_pack_data[key][3] = ids_from_pack_in_gaia_results
                    else:
                        # Set it to zero
                        more_from_pack_data[key][0] = 0
                        more_from_pack_data[key][3] = []
        except SimilarityException, e:
            if e.status_code == 500:
                raise ServerErrorException(msg=e.message)
            elif e.status_code == 400:
                raise InvalidUrlException(msg=e.message)
            elif e.status_code == 404:
                raise NotFoundException(msg=e.message)
            else:
                raise ServerErrorException(msg=e.message)
        except Exception, e:
            if settings.DEBUG:
                raise ServerErrorException(msg=e.message)
            else:
                raise ServerErrorException()


        if search_form.cleaned_data['target'] or target_file:
            # Combined search, sort by gaia_ids
            results_a = gaia_ids
            results_b = solr_ids
        else:
            # Combined search, sort by solr ids
            results_a = solr_ids
            results_b = gaia_ids

        # Combine results
        results_b_set = set(results_b)
        combined_ids = [id for id in results_a if id in results_b_set]
        combined_count = len(combined_ids)
        return combined_ids[(search_form.cleaned_data['page'] - 1) * search_form.cleaned_data['page_size']:search_form.cleaned_data['page'] * search_form.cleaned_data['page_size']], \
               combined_count, \
               distance_to_target_data, \
               more_from_pack_data, \
               note


###############
# OTHER UTILS
###############

# General utils
###############

def prepend_base(rel):
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
            client_id = request.auth.id
        elif auth_method_name == "Token":
            user = None
            developer = request.auth.user
            client_id = request.auth.id
        elif auth_method_name == "Session":
            user = request.user
            developer = None
            client_id = None

    return auth_method_name, developer, user, client_id


def basic_request_info_for_log_message(auth_method_name, developer, user, client_id):
    return 'ApiV2 Auth:%s Dev:%s User:%s Client:%s' % (auth_method_name, developer, user, str(client_id))


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

def get_formatted_examples_for_view(view_name, max=10):
    try:
        data = examples[view_name]
    except:
        print 'Could not find examples for view %s' % view_name
        return ''

    count = 0
    output = 'Some quick examples:<div class="request-info" style="clear: both"><pre class="prettyprint">'
    for description, elements in data:
        for element in elements:
            if count >= max:
                break

            if element[0:5] == 'apiv2':
                output += '<span class="pln"><a href="%s">%s</a></span><br>' % (prepend_base('/' + element), prepend_base('/' + element))
            else:
                output += '<span class="pln">%s</span><br>' % (element % prepend_base(''))
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

def create_sound_object(user, original_sound_fields):
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
        raise ServerErrorException(msg=msg)

    sound_already_exists = Sound.objects.filter(md5=sound.md5).exists()
    if sound_already_exists:
        os.remove(sound.original_path)
        raise OtherException("Sound could not be created because the uploaded file is already part of freesound.")

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
            raise ServerErrorException(msg=msg)
        sound.original_path = new_original_path
        sound.save()

    # 6 create pack if it does not exist
    if 'pack' in sound_fields:
        if Pack.objects.filter(name=sound_fields['pack'], user=user).exists():
            p = Pack.objects.get(name=sound_fields['pack'], user=user)
        else:
            p, created = Pack.objects.get_or_create(user=user, name=sound_fields['pack'])
        sound.pack = p

    # 7 create geotag objects
    # format: lat#lon#zoom
    if 'geotag' in sound_fields:
        lat, lon, zoom = sound_fields['geotag'].split(',')
        geotag = GeoTag(user=user,
            lat=float(lat),
            lon=float(lon),
            zoom=int(zoom))
        geotag.save()
        sound.geotag = geotag

    # 8 set description, tags
    sound.description = sound_fields['description']
    sound.set_tags([t.lower() for t in sound_fields['tags'].split(" ") if t])

    # 9 save!
    sound.save()

    # 10 Proces
    try:
        sound.compute_crc()
    except:
        pass

    try:
        sound.process()
    except Exception, e:
        pass

    # Set moderation state to OK (this is just for testing)
    #sound.moderation_state = 'OK'
    #sound.processing_state = 'OK'
    #sound.save()

    return sound