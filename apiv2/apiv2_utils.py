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

from rest_framework.generics import GenericAPIView as RestFrameworkGenericAPIView, ListAPIView as RestFrameworkListAPIView, RetrieveAPIView as RestFrameworkRetrieveAPIView
from django.http import JsonResponse, HttpResponseRedirect
from apiv2.authentication import OAuth2Authentication, TokenAuthentication, SessionAuthentication
import combined_search_strategies
from oauth2_provider.generators import BaseHashGenerator
from oauthlib.common import generate_client_id as oauthlib_generate_client_id
from oauthlib.common import UNICODE_ASCII_CHARACTER_SET
from exceptions import *
from examples import examples
from django.conf import settings
from utils.similarity_utilities import get_sounds_descriptors
from utils.search.solr import Solr, SolrException, SolrResponseInterpreter
from search.views import search_prepare_query
from utils.similarity_utilities import api_search as similarity_api_search
from similarity.client import SimilarityException
from urllib import unquote
from django.contrib.sites.models import Site
from django.urls import resolve
from rest_framework.renderers import BrowsableAPIRenderer
from utils.logging_filters import get_client_ip
import urlparse
import logging
import json

logger_error = logging.getLogger("api_errors")


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


#############################
# Rest Framework custom views
#############################


class GenericAPIView(RestFrameworkGenericAPIView):
    throttling_rates_per_level = settings.APIV2_BASIC_THROTTLING_RATES_PER_LEVELS
    authentication_classes = (OAuth2Authentication, TokenAuthentication, SessionAuthentication)
    queryset = False

    def initial(self, request, *args, **kwargs):
        super(GenericAPIView, self).initial(request, *args, **kwargs)

        # Get request information and store it as class variable
        self.end_user_ip = get_client_ip(request)
        self.auth_method_name, self.developer, self.user, self.client_id, self.client_name, self.protocol,\
            self.contains_www = get_authentication_details_form_request(request)

    def log_message(self, message):
        return log_message_helper(message, resource=self)

    def finalize_response(self, request, response, *args, **kwargs):
        """ This method is overriden to make a redirect when the user is using the interactive API browser and
        with 'www' sub-domain. The problem is that we can't check if it's accessing through the interactive browser
        inside the 'initial' method because it raises an exception when the user is not logged in, that exception is
        handled by 'finalize_response' method of APIView.
        """
        response = super(GenericAPIView, self).finalize_response(request, response, *args, **kwargs)

        # If the user is using the interactive API browser and the www in the domain we redirect to nowww.
        host = request.get_host()
        if type(response.accepted_renderer) == type(BrowsableAPIRenderer()) and 'www' in host:
            domain = "https://%s" % Site.objects.get_current().domain
            return_url = urlparse.urljoin(domain, request.get_full_path())
            return HttpResponseRedirect(return_url)
        return response


class OauthRequiredAPIView(RestFrameworkGenericAPIView):
    throttling_rates_per_level = settings.APIV2_BASIC_THROTTLING_RATES_PER_LEVELS
    authentication_classes = (OAuth2Authentication, SessionAuthentication)

    def initial(self, request, *args, **kwargs):
        super(OauthRequiredAPIView, self).initial(request, *args, **kwargs)

        # Get request information and store it as class variable
        self.end_user_ip = get_client_ip(request)
        self.auth_method_name, self.developer, self.user, self.client_id, self.client_name, self.protocol,\
            self.contains_www = get_authentication_details_form_request(request)

        # Check if using https
        throw_exception_if_not_https(request)

    def log_message(self, message):
        return log_message_helper(message, resource=self)


class DownloadAPIView(OauthRequiredAPIView):
    throttling_rates_per_level = settings.APIV2_BASIC_THROTTLING_RATES_PER_LEVELS


class WriteRequiredGenericAPIView(RestFrameworkGenericAPIView):
    throttling_rates_per_level = settings.APIV2_POST_THROTTLING_RATES_PER_LEVELS
    authentication_classes = (OAuth2Authentication, SessionAuthentication)

    def initial(self, request, *args, **kwargs):
        super(WriteRequiredGenericAPIView, self).initial(request, *args, **kwargs)

        # Get request informationa dn store it as class variable
        self.end_user_ip = get_client_ip(request)
        self.auth_method_name, self.developer, self.user, self.client_id, self.client_name, self.protocol, \
            self.contains_www = get_authentication_details_form_request(request)

        # Check if using https
        throw_exception_if_not_https(request)

        # Check if client has write permissions
        if self.auth_method_name == "OAuth2":
            if "write" not in request.auth.scopes:
                raise UnauthorizedException(resource=self)

    def log_message(self, message):
        return log_message_helper(message, resource=self)


class ListAPIView(RestFrameworkListAPIView):
    throttling_rates_per_level = settings.APIV2_BASIC_THROTTLING_RATES_PER_LEVELS
    authentication_classes = (OAuth2Authentication, TokenAuthentication, SessionAuthentication)

    def initial(self, request, *args, **kwargs):
        super(ListAPIView, self).initial(request, *args, **kwargs)

        # Get request information and store it as class variable
        self.end_user_ip = get_client_ip(request)
        self.auth_method_name, self.developer, self.user, self.client_id, self.client_name, self.protocol,\
            self.contains_www = get_authentication_details_form_request(request)

    def log_message(self, message):
        return log_message_helper(message, resource=self)


class RetrieveAPIView(RestFrameworkRetrieveAPIView):
    throttling_rates_per_level = settings.APIV2_BASIC_THROTTLING_RATES_PER_LEVELS
    authentication_classes = (OAuth2Authentication, TokenAuthentication, SessionAuthentication)

    def initial(self, request, *args, **kwargs):
        super(RetrieveAPIView, self).initial(request, *args, **kwargs)

        # Get request information and store it as class variable
        self.end_user_ip = get_client_ip(request)
        self.auth_method_name, self.developer, self.user, self.client_id, self.client_name, self.protocol, \
            self.contains_www = get_authentication_details_form_request(request)

    def log_message(self, message):
        return log_message_helper(message, resource=self)


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
            data_dict.pop('token', None)  # Remove token from req params if it exists (we don't need it)
    if info_dict is None:
        if resource is not None:
            info_dict = build_info_dict(resource=resource)
        if request is not None and info_dict is None:
            info_dict = build_info_dict(request=request)

    return '%s #!# %s #!# %s' % (message, json.dumps(data_dict), json.dumps(info_dict))


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


def throw_exception_if_not_https(request):
    if not settings.DEBUG:
        if not request.is_secure():
            raise RequiresHttpsException(request=request)


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

    analysis_data_required = 'analysis' in view.request.query_params.get('fields', '').split(',')
    if analysis_data_required:
        # Get ids of the particular sounds we need
        if queryset:
            paginated_queryset = view.paginate_queryset(queryset)
            ids = [int(sound.id) for sound in paginated_queryset]
        else:
            ids = [int(sid) for sid in sound_ids]

        # Get descriptor values for the required ids
        # Required descriptors are indicated with the parameter 'descriptors'. If 'descriptors' is empty, we return nothing
        descriptors = view.request.query_params.get('descriptors', [])
        view.sound_analysis_data = {}
        if descriptors:
            try:
                view.sound_analysis_data = get_sounds_descriptors(ids,
                                                                  descriptors.split(','),
                                                                  view.request.query_params.get('normalized', '0') == '1',
                                                                  only_leaf_descriptors=True)
            except:
                pass
        else:
            for id in ids:
                view.sound_analysis_data[str(id)] = 'No descriptors specified. You should indicate which descriptors you want with the \'descriptors\' request parameter.'


# APIv1 end of life
###################

apiv1_logger = logging.getLogger("api")


def apiv1_end_of_life_message(request):
    apiv1_logger.error('410 API error: End of life')
    content = {
        "explanation": "Freesound APIv1 has reached its end of life and is no longer available."
        "Please, upgrade to Freesound APIv2. More information: http://www.freesound.org/docs/api/"
    }
    return JsonResponse(content, status=410)
