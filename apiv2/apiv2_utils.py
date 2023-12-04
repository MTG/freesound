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

import collections
import datetime
import json
import logging
import math
import urllib.parse
from urllib.parse import unquote

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache, caches
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import resolve
from django.utils.encoding import smart_str
from oauth2_provider.generators import BaseHashGenerator
from oauthlib.common import UNICODE_ASCII_CHARACTER_SET
from oauthlib.common import generate_client_id as oauthlib_generate_client_id
from rest_framework.generics import GenericAPIView as RestFrameworkGenericAPIView, \
    ListAPIView as RestFrameworkListAPIView, RetrieveAPIView as RestFrameworkRetrieveAPIView
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.utils import formatting

from . import combined_search_strategies
from apiv2.forms import API_SORT_OPTIONS_MAP
from apiv2.authentication import OAuth2Authentication, TokenAuthentication, SessionAuthentication
from apiv2.exceptions import RequiresHttpsException, UnauthorizedException, ServerErrorException, BadRequestException, \
    NotFoundException
from .examples import examples
from similarity.client import SimilarityException
from utils.encryption import create_hash
from utils.logging_filters import get_client_ip
from utils.search import SearchEngineException, get_search_engine
from utils.search.search_sounds import parse_weights_parameter
from utils.similarity_utilities import api_search as similarity_api_search
from utils.similarity_utilities import get_sounds_descriptors

error_logger = logging.getLogger("api_errors")
cache_api_monitoring = caches["api_monitoring"]


##########################################
# oauth 2 provider generator for client id
##########################################

class FsClientIdGenerator(BaseHashGenerator):
    def hash(self):
        """
        Override ClientIdGenerator from oauth_provider2 as it does not allow to change length of id with
        a setting.
        """
        return oauthlib_generate_client_id(length=20, chars=UNICODE_ASCII_CHARACTER_SET)


#########################################################################################
# Rest Framework custom function for getting descriptions from function instead docstring
#########################################################################################

def get_view_description(cls, html=False):
    description = ''
    if getattr(cls, 'get_description', None):
        cache_key = create_hash(cls.get_view_name(), limit=32)
        cached_description = cache.get(cache_key)
        if not cached_description:
            description = cls.get_description()
            description = formatting.dedent(smart_str(description))
            # Cache for 1 hour (if we update description, it will take 1 hour to show)
            cache.set(cache_key, description, 60*60)
        else:
            description = cached_description
    if html:
        return formatting.markup_description(description)
    return description


#############################
# Rest Framework custom views
#############################


class FreesoundAPIViewMixin:
    end_user_ip = None
    auth_method_name = None
    developer = None
    user = None
    client_id = None
    client_name = None
    protocol = None
    contains_www = None

    def log_message(self, message):
        return log_message_helper(message, resource=self)

    def store_monitor_usage(self):
        """This function increases the counter of requests per API client that is stored in the cache.
        This function is expected to be called everytime an API request is received, it generates a key for the
        current daily count (composed of the current date and the API client id) and increases the count stored in
        the cache by one.

        A Django management command is expected to run periodically to take the information from the cache
        and store it in the DB. The management command should run at least once a day, and it will consolidate
        API usage counts for the last 2 days (see consolidate_api_usage_data.py for more info). The cache entries
        set by this function expire in 72 hours so the management command has time to consolidate the results of the
        previous days.
        """
        if self.client_id is not None:
            now = datetime.datetime.now().date()
            monitoring_key = f'{now.year}-{now.month}-{now.day}_{self.client_id}'
            current_value = cache_api_monitoring.get(monitoring_key, 0)
            cache_api_monitoring.set(monitoring_key, current_value + 1, 60 * 60 * 24 * 3)  # Expire in 3 days

    def get_request_information(self, request):
        # Get request information and store it as class variable
        # This information is mainly useful for logging
        self.end_user_ip = get_client_ip(request)
        self.auth_method_name, self.developer, self.user, self.client_id, self.client_name, self.protocol, \
            self.contains_www = get_authentication_details_form_request(request)

    def redirect_if_needed(self, request, response):
        """Returns HttpResponseRedirect if the current request should be redirected

        This methods returns an HttpResponseRedirect if:
            1) user is using the browseable API and the www domain
            2) user is using the browseable API and HTTP

        The redirect is done to no-www and HTTPS. This is implemented here because, for compatibility reasons, the API
        is the only part of Freesound which is not autotmatically redriected to HTTPS/no-www. However, when users are
        browsing the API interactively (with the browser), we want this behvaiour top be applied.
        """

        if isinstance(response.accepted_renderer, BrowsableAPIRenderer):
            if request.get_host().startswith('www'):
                domain = f"{'https' if not settings.DEBUG else 'http'}://{Site.objects.get_current().domain}"
                return_url = urllib.parse.urljoin(domain, request.get_full_path())
                return HttpResponseRedirect(return_url)
            if request.scheme != 'https' and not settings.DEBUG:
                domain = f"https://{Site.objects.get_current().domain}"
                return_url = urllib.parse.urljoin(domain, request.get_full_path())
                return HttpResponseRedirect(return_url)
        return response

    def throw_exception_if_not_https(self, request):
        if not settings.DEBUG:
            if not request.is_secure():
                raise RequiresHttpsException(request=request)


class GenericAPIView(RestFrameworkGenericAPIView, FreesoundAPIViewMixin):
    throttling_rates_per_level = settings.APIV2_BASIC_THROTTLING_RATES_PER_LEVELS
    authentication_classes = (OAuth2Authentication, TokenAuthentication, SessionAuthentication)
    queryset = False

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.get_request_information(request)
        self.store_monitor_usage()

    def finalize_response(self, request, response, *args, **kwargs):
        """ This method is overriden to make a redirect when the user is using the interactive API browser and
        with 'www' sub-domain. The problem is that we can't check if it's accessing through the interactive browser
        inside the 'initial' method because it raises an exception when the user is not logged in, that exception is
        handled by 'finalize_response' method of APIView.
        """
        response = super().finalize_response(request, response, *args, **kwargs)
        response = self.redirect_if_needed(request, response)
        return response


class OauthRequiredAPIView(RestFrameworkGenericAPIView, FreesoundAPIViewMixin):
    throttling_rates_per_level = settings.APIV2_BASIC_THROTTLING_RATES_PER_LEVELS
    authentication_classes = (OAuth2Authentication, SessionAuthentication)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.get_request_information(request)
        self.throw_exception_if_not_https(request)
        self.store_monitor_usage()

    def finalize_response(self, request, response, *args, **kwargs):
        # See comment in GenericAPIView.finalize_response
        response = super().finalize_response(request, response, *args, **kwargs)
        response = self.redirect_if_needed(request, response)
        return response


class DownloadAPIView(RestFrameworkGenericAPIView, FreesoundAPIViewMixin):
    throttling_rates_per_level = settings.APIV2_BASIC_THROTTLING_RATES_PER_LEVELS
    authentication_classes = (OAuth2Authentication, SessionAuthentication)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.get_request_information(request)
        self.throw_exception_if_not_https(request)
        self.store_monitor_usage()

    # NOTE: don't override finalize_response here as we are returning a file and not the browseable api response.
    # There is no need to check for www/non-www host here.


class WriteRequiredGenericAPIView(RestFrameworkGenericAPIView, FreesoundAPIViewMixin):
    throttling_rates_per_level = settings.APIV2_POST_THROTTLING_RATES_PER_LEVELS
    authentication_classes = (OAuth2Authentication, SessionAuthentication)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.get_request_information(request)
        self.throw_exception_if_not_https(request)
        self.store_monitor_usage()

        # Check if client has write permissions
        if self.auth_method_name == "OAuth2":
            if "write" not in request.auth.scopes:
                raise UnauthorizedException(resource=self)

    def finalize_response(self, request, response, *args, **kwargs):
        # See comment in GenericAPIView.finalize_response
        response = super().finalize_response(request, response, *args, **kwargs)
        response = self.redirect_if_needed(request, response)
        return response


class ListAPIView(RestFrameworkListAPIView, FreesoundAPIViewMixin):
    throttling_rates_per_level = settings.APIV2_BASIC_THROTTLING_RATES_PER_LEVELS
    authentication_classes = (OAuth2Authentication, TokenAuthentication, SessionAuthentication)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.get_request_information(request)
        self.store_monitor_usage()

    def get_serializer(self, *args, **kwargs):
        # Overwrite DRF's get_serializer method so that we add sound analysis information when requested
        serializer_class = self.get_serializer_class()
        kwargs['context'] = self.get_serializer_context()
        if 'SoundListSerializer' in str(serializer_class):
            # If we are trying to serialize sounds, check if we should and sound analysis data to them and add it
            if isinstance(args[0], collections.abc.Iterable):
                sound_analysis_data = get_analysis_data_for_sound_ids(kwargs['context']['request'], sound_ids=[s.id for s in args[0]])
                if sound_analysis_data:
                    kwargs['sound_analysis_data'] = sound_analysis_data
        return serializer_class(*args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):
        # See comment in GenericAPIView.finalize_response
        response = super().finalize_response(request, response, *args, **kwargs)
        response = self.redirect_if_needed(request, response)
        return response


class RetrieveAPIView(RestFrameworkRetrieveAPIView, FreesoundAPIViewMixin):
    throttling_rates_per_level = settings.APIV2_BASIC_THROTTLING_RATES_PER_LEVELS
    authentication_classes = (OAuth2Authentication, TokenAuthentication, SessionAuthentication)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.get_request_information(request)
        self.store_monitor_usage()

    def finalize_response(self, request, response, *args, **kwargs):
        # See comment in GenericAPIView.finalize_response
        response = super().finalize_response(request, response, *args, **kwargs)
        response = self.redirect_if_needed(request, response)
        return response


##################
# Search utilities
##################

def api_search(
        search_form, target_file=None, extra_parameters=False, merging_strategy='merge_optimized', resource=None):

    if search_form.cleaned_data['query']  is None \
            and search_form.cleaned_data['filter'] is None \
            and not search_form.cleaned_data['descriptors_filter'] \
            and not search_form.cleaned_data['target'] \
            and not target_file:
        # No input data for search, return empty results
        return [], 0, None, None, None, None, None

    if search_form.cleaned_data['query'] is None and search_form.cleaned_data['filter'] is None:
        # Standard content-based search
        try:
            results, count, note = similarity_api_search(
                target=search_form.cleaned_data['target'],
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
        except SimilarityException as e:
            if e.status_code == 500:
                raise ServerErrorException(msg=str(e), resource=resource)
            elif e.status_code == 400:
                raise BadRequestException(msg=str(e), resource=resource)
            elif e.status_code == 404:
                raise NotFoundException(msg=str(e), resource=resource)
            else:
                raise ServerErrorException(msg=f'Similarity server error: {str(e)}', resource=resource)
        except Exception as e:
            raise ServerErrorException(
                msg='The similarity server could not be reached or some unexpected error occurred.', resource=resource)

    elif not search_form.cleaned_data['descriptors_filter'] \
            and not search_form.cleaned_data['target'] \
            and not target_file:

        # Standard text-based search
        try:
            # We need to convert the sort parameter to standard sorting options from
            # settings.SEARCH_SOUNDS_SORT_OPTION_X. Therefore here we convert to the standard names and later
            # the get_search_engine().search_sounds() function will convert it back to search engine meaningful names
            processed_sort = API_SORT_OPTIONS_MAP[search_form.cleaned_data['sort'][0]]
            result = get_search_engine().search_sounds(
                textual_query=unquote(search_form.cleaned_data['query'] or ""),
                query_filter=unquote(search_form.cleaned_data['filter'] or ""),
                query_fields=parse_weights_parameter(search_form.cleaned_data['weights']),
                sort=processed_sort,
                offset=(search_form.cleaned_data['page'] - 1) * search_form.cleaned_data['page_size'],
                num_sounds=search_form.cleaned_data['page_size'],
                group_by_pack=search_form.cleaned_data['group_by_pack']
            )
            ids_score = [(int(element['id']), element['score']) for element in result.docs]
            num_found = result.num_found
            more_from_pack_data = None
            if search_form.cleaned_data['group_by_pack']:
                # If grouping option is on, store grouping info in a dictionary that we can add when serializing sounds
                more_from_pack_data = {
                    int(group['id']): [group['n_more_in_group'], group['group_name']] for group in result.docs
                }

            return ids_score, num_found, None, more_from_pack_data, None, None, None

        except SearchEngineException as e:
            if search_form.cleaned_data['filter'] is not None:
                raise BadRequestException(msg='Search server error: %s (please check that your filter syntax and field '
                                              'names are correct)' % str(e), resource=resource)
            raise BadRequestException(msg=f'Search server error: {str(e)}', resource=resource)
        except Exception as e:
            print(e)
            raise ServerErrorException(
                msg='The search server could not be reached or some unexpected error occurred.', resource=resource)

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


def log_message_helper(message, data_dict=None, info_dict=None, resource=None, request=None):
    """
    In this helper a string is generated in the right format to be parsed by graylog, containing a key which
    indicates the operation and two dicts with the following information:
    - If data_dict is None the first dict contains the query data taken from the request params
    - If info_dict is None the second dict contains more data from the api client
    """
    if data_dict is None:
        if resource is not None:
            data_dict = resource.request.query_params.copy()
            data_dict = {key: urllib.parse.quote(value, safe=",:") for key, value in data_dict.items()}
            data_dict.pop('token', None)  # Remove token from req params if it exists (we don't need it)
    if info_dict is None:
        if resource is not None:
            info_dict = build_info_dict(resource=resource)
        if request is not None and info_dict is None:
            info_dict = build_info_dict(request=request)

    return f'{message} #!# {json.dumps(data_dict)} #!# {json.dumps(info_dict)}'


def build_info_dict(resource=None, request=None):
    if resource is not None:
        return {
            'api_version': 'v2',
            'api_auth_type': resource.auth_method_name,
            'api_client_username': str(resource.developer),
            'api_enduser_username': str(resource.user),
            'api_client_id': resource.client_id,
            'api_client_name': resource.client_name,
            'ip': resource.end_user_ip,
            'api_request_protocol': resource.protocol,
            'api_www': resource.contains_www
        }
    if request is not None:
        auth_method_name, developer, user, client_id, client_name, protocol,\
            contains_www = get_authentication_details_form_request(request)
        return {
            'api_version': 'v2',
            'api_auth_type': auth_method_name,
            'api_client_username': str(developer),
            'api_enduser_username': str(user),
            'api_client_id': client_id,
            'api_client_name': client_name,
            'ip': get_client_ip(request),
            'api_request_protocol': protocol,
            'api_www': contains_www
        }


def prepend_base(rel, dynamic_resolve=True, use_https=False, request_is_secure=False):

    if rel.startswith('http'):
        # If "rel" URL is not really a relative path but an absolute URL, return it directly
        # This happens for example with URLs to serve static files from a CDN, which have a different
        # domain name that the API endpoints
        return rel

    if request_is_secure:
        use_https = True
        dynamic_resolve = False  # don't need to dynamic resolve is request is https

    if dynamic_resolve:
        use_https = True

    if use_https:
        return f"https://{Site.objects.get_current().domain}{rel}"
    else:
        return f"http://{Site.objects.get_current().domain}{rel}"


def get_authentication_details_form_request(request):
    auth_method_name = None
    user = None
    developer = None
    client_id = None
    client_name = None
    protocol = "https" if request.is_secure() else "http"
    contains_www = 'www' if 'www' in request.get_host() else 'none'

    if request.successful_authenticator:
        auth_method_name = request.successful_authenticator.authentication_method_name
        if auth_method_name == "OAuth2":
            user = request.user
            developer = request.auth.application.user
            client_id = request.auth.application.apiv2_client.client_id
            client_name = request.auth.application.apiv2_client.name
        elif auth_method_name == "Token":
            user = None
            developer = request.auth.user
            client_id = request.auth.client_id
            client_name = request.auth.name
        elif auth_method_name == "Session":
            user = request.user
            developer = None
            client_id = None
            client_name = None

    return auth_method_name, developer, user, client_id, client_name, protocol, contains_www


def request_parameters_info_for_log_message(get_parameters):
    return ','.join([f'{key}={value}' for key, value in get_parameters.items()])


class ApiSearchPaginator:
    def __init__(self, results, count, num_per_page):
        self.num_per_page = num_per_page
        self.count = count
        self.num_pages = math.ceil(count / num_per_page)
        self.page_range = list(range(1, self.num_pages + 1))
        self.results = results

    def page(self, page_num):
        has_next = page_num < self.num_pages
        has_previous = 1 < page_num <= self.num_pages

        return {'object_list': self.results,
                'has_next': has_next,
                'has_previous': has_previous,
                'has_other_pages': has_next or has_previous,
                'next_page_number': page_num + 1,
                'previous_page_number': page_num - 1,
                'page_num': page_num}


# Docs examples utils
#####################

def get_formatted_examples_for_view(view_name, url_name, max=10):
    try:
        data = examples[view_name]
    except:
        return ''

    count = 0
    output = 'Some quick examples:<div class="request-info" style="clear: both"><pre class="prettyprint">'

    for description, elements in data:
        for element in elements:
            if count >= max:
                break

            if element[0:5] == 'apiv2':
                url = prepend_base('/' + element, dynamic_resolve=False, use_https=True)
                output += f'<span class="pln"><a href="{url}">{url}</a></span><br>'
            else:
                # This is only apiv2 oauth examples
                url = prepend_base('', dynamic_resolve=False, use_https=True)
                output += f'<span class="pln">{element % url}</span><br>'
            count += 1

    output += '</pre></div>'

    return output


# Similarity utils
##################

def get_analysis_data_for_sound_ids(request, sound_ids=[]):
    # Get analysis data for all requested sounds and return it as a dictionary    
    sound_analysis_data = {}
    analysis_data_is_requested = 'analysis' in request.query_params.get('fields', '').split(',')
    if analysis_data_is_requested:
        descriptors = request.query_params.get('descriptors', '')
        normalized = request.query_params.get('normalized', '0') == '1'
        ids = [int(sid) for sid in sound_ids]
        if descriptors:
            try:
                sound_analysis_data = get_sounds_descriptors(ids, descriptors.split(','), normalized, only_leaf_descriptors=True)
            except:
                pass
        else:
            for id in ids:
                sound_analysis_data[str(id)] = 'No descriptors specified. You should indicate which descriptors ' \
                                                    'you want with the \'descriptors\' request parameter.'
    return sound_analysis_data



# APIv1 end of life
###################

apiv1_logger = logging.getLogger("api")


def apiv1_end_of_life_message(request):
    apiv1_logger.info('410 API error: End of life')
    content = {
        "explanation": "Freesound APIv1 has reached its end of life and is no longer available."
        "Please, upgrade to Freesound APIv2. More information: https://freesound.org/docs/api/"
    }
    return JsonResponse(content, status=410)
