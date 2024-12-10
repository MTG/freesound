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

import datetime
import json
import logging
import math
import os
from collections import OrderedDict
from urllib.parse import quote

import jwt
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Exists, OuterRef
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render 
from django.urls import reverse
from oauth2_provider.models import Grant, AccessToken
from oauth2_provider.views import AuthorizationView as ProviderAuthorizationView
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, throttle_classes, permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

import utils.sound_upload
from accounts.views import handle_uploaded_file
from apiv2.authentication import OAuth2Authentication, TokenAuthentication, SessionAuthentication
from apiv2.exceptions import NotFoundException, InvalidUrlException, BadRequestException, ConflictException, \
    UnauthorizedException, ServerErrorException, OtherException, APIException
from apiv2.forms import ApiV2ClientForm, SoundCombinedSearchFormAPI, SoundTextSearchFormAPI, \
    SoundContentSearchFormAPI, SimilarityFormAPI
from apiv2.models import ApiV2Client
from apiv2.serializers import SimilarityFileSerializer, UploadAndDescribeAudioFileSerializer, \
    EditSoundDescriptionSerializer, SoundDescriptionSerializer, CreateCommentSerializer, SoundCommentsSerializer, \
    CreateRatingSerializer, CreateBookmarkSerializer, BookmarkCategorySerializer, PackSerializer, UserSerializer, \
    SoundSerializer, SoundListSerializer
from .apiv2_utils import GenericAPIView, ListAPIView, RetrieveAPIView, WriteRequiredGenericAPIView, \
    OauthRequiredAPIView, DownloadAPIView, get_analysis_data_for_sound_ids, api_search, \
    ApiSearchPaginator, get_sounds_descriptors, prepend_base, get_formatted_examples_for_view
from bookmarks.models import Bookmark, BookmarkCategory
from comments.models import Comment
from geotags.models import GeoTag
from ratings.models import SoundRating
from similarity.client import Similarity
from sounds.models import Sound, Pack, License, SoundAnalysis
from utils.downloads import download_sounds
from utils.filesystem import generate_tree
from utils.nginxsendfile import sendfile, prepare_sendfile_arguments_for_sound_download
from utils.tags import clean_and_split_tags

api_logger = logging.getLogger("api")
resources_doc_filename = 'resources_apiv2.html'


class AuthorizationView(ProviderAuthorizationView):
    login_url = '/apiv2/login/'

####################################
# SEARCH AND SIMILARITY SEARCH VIEWS
####################################


class TextSearch(GenericAPIView):

    @classmethod
    def get_description(cls):
        return 'Search sounds in Freesound based on their tags and other metadata.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#text-search' % resources_doc_filename,
                  get_formatted_examples_for_view('TextSearch', 'apiv2-sound-search', max=5))

    def get(self, request,  *args, **kwargs):
        api_logger.info(self.log_message('search'))

        # Validate search form and check page 0
        search_form = SoundTextSearchFormAPI(request.query_params)
        if not search_form.is_valid():
            raise BadRequestException(msg='Malformed request.', resource=self)
        if search_form.cleaned_data['query'] is None and search_form.cleaned_data['filter'] is None:
            raise BadRequestException(msg='At least one request parameter from Text Search should be included '
                                          'in the request.', resource=self)
        if search_form.cleaned_data['page'] < 1:
            raise NotFoundException(resource=self)
        if search_form.cleaned_data['page_size'] < 1:
            raise NotFoundException(resource=self)

        # Get search results
        try:
            results, count, distance_to_target_data, more_from_pack_data, note, params_for_next_page, debug_note = \
                api_search(search_form, resource=self)
        except APIException as e:
            raise e
        except Exception as e:
            raise ServerErrorException(msg='Unexpected error', resource=self)

        # Paginate results
        paginator = ApiSearchPaginator(results, count, search_form.cleaned_data['page_size'])
        if search_form.cleaned_data['page'] > paginator.num_pages and count != 0:
            raise NotFoundException(resource=self)
        page = paginator.page(search_form.cleaned_data['page'])
        response_data = dict()
        response_data['count'] = paginator.count
        response_data['previous'] = None
        response_data['next'] = None
        if page['has_other_pages']:
                if page['has_previous']:
                    response_data['previous'] = search_form.construct_link(reverse('apiv2-sound-text-search'),
                                                                           page=page['previous_page_number'])
                if page['has_next']:
                    response_data['next'] = search_form.construct_link(reverse('apiv2-sound-text-search'),
                                                                       page=page['next_page_number'])

        # Get analysis data and serialize sound results
        object_list = [ob for ob in page['object_list']]
        id_score_map = dict(object_list)
        sound_ids = [ob[0] for ob in object_list]
        sound_analysis_data = get_analysis_data_for_sound_ids(request, sound_ids=sound_ids)
        # In search queries, only include audio analyers's output if requested through the fields parameter
        needs_analyzers_ouptut = 'analyzers_output' in search_form.cleaned_data.get('fields', '') or 'ac_analysis' in search_form.cleaned_data.get('fields', '')
        sounds_dict = Sound.objects.dict_ids(sound_ids=sound_ids, include_analyzers_output=needs_analyzers_ouptut)
        sounds = []
        for i, sid in enumerate(sound_ids):
            try:
                sound = SoundListSerializer(sounds_dict[sid], context=self.get_serializer_context(), score_map=id_score_map, sound_analysis_data=sound_analysis_data).data
                if more_from_pack_data:
                    if more_from_pack_data[sid][0]:
                        pack_id =  more_from_pack_data[sid][1][:more_from_pack_data[sid][1].find("_")]
                        pack_name = more_from_pack_data[sid][1][more_from_pack_data[sid][1].find("_")+1:]
                        sound['more_from_same_pack'] = search_form.construct_link(
                            reverse('apiv2-sound-text-search'),
                            page=1,
                            filt='grouping_pack:"%i_%s"' % (int(pack_id), pack_name),
                            group_by_pack='0')
                        sound['n_from_same_pack'] = more_from_pack_data[sid][0] + 1  # we add one as is the sound itself
                sounds.append(sound)
            except KeyError:
                # This will happen if there are synchronization errors between solr index, gaia and the database.
                # In that case sounds are set to null
                sounds.append(None)
        response_data['results'] = sounds

        if note:
            response_data['note'] = note

        return Response(response_data, status=status.HTTP_200_OK)


class ContentSearch(GenericAPIView):

    @classmethod
    def get_description(cls):
        return 'Search sounds in Freesound based on their content descriptors.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#content-search' % resources_doc_filename,
                  get_formatted_examples_for_view('ContentSearch', 'apiv2-sound-content-search', max=5))

    serializer_class = SimilarityFileSerializer
    analysis_file = None

    def get(self, request,  *args, **kwargs):
        api_logger.info(self.log_message('content_search'))

        # Validate search form and check page 0
        search_form = SoundContentSearchFormAPI(request.query_params)
        if not search_form.is_valid():
            raise BadRequestException(msg='Malformed request.', resource=self)
        if not search_form.cleaned_data['target'] and \
                not search_form.cleaned_data['descriptors_filter'] and \
                not self.analysis_file:
            raise BadRequestException(msg='At least one parameter from Content Search should be included '
                                          'in the request.', resource=self)
        if search_form.cleaned_data['page'] < 1:
            raise NotFoundException(resource=self)

        # Get search results
        analysis_file = None
        if self.analysis_file:
            analysis_file = self.analysis_file.read()
        try:
            results, count, distance_to_target_data, more_from_pack_data, note, params_for_next_page, debug_note = \
                api_search(search_form, target_file=analysis_file, resource=self)
        except APIException as e:
            raise e # TODO pass correct exception message
        except Exception as e:
            raise ServerErrorException(msg='Unexpected error', resource=self)

        # Paginate results
        paginator = ApiSearchPaginator(results, count, search_form.cleaned_data['page_size'])
        if search_form.cleaned_data['page'] > paginator.num_pages and count != 0:
            raise NotFoundException(resource=self)
        page = paginator.page(search_form.cleaned_data['page'])
        response_data = dict()
        if self.analysis_file:
            response_data['target_analysis_file'] = f'{self.analysis_file.name} ({self.analysis_file.size // 1024:d} KB)'
        response_data['count'] = paginator.count
        response_data['previous'] = None
        response_data['next'] = None
        if page['has_other_pages']:
                if page['has_previous']:
                    response_data['previous'] = search_form.construct_link(reverse('apiv2-sound-content-search'),
                                                                           page=page['previous_page_number'])
                if page['has_next']:
                    response_data['next'] = search_form.construct_link(reverse('apiv2-sound-content-search'),
                                                                       page=page['next_page_number'])

        # Get analysis data and serialize sound results
        ids = [id for id in page['object_list']]
        sound_analysis_data = get_analysis_data_for_sound_ids(request, sound_ids=ids)
        # In search queries, only include audio analyers's output if requested through the fields parameter
        needs_analyzers_ouptut = 'analyzers_output' in search_form.cleaned_data.get('fields', '') or 'ac_analysis' in search_form.cleaned_data.get('fields', '')
        sounds_dict = Sound.objects.dict_ids(sound_ids=ids, include_analyzers_output=needs_analyzers_ouptut)

        sounds = []
        for i, sid in enumerate(ids):
            try:
                sound = SoundListSerializer(sounds_dict[sid], context=self.get_serializer_context(), sound_analysis_data=sound_analysis_data).data
                # Distance to target is present we add it to the serialized sound
                if distance_to_target_data:
                    sound['distance_to_target'] = distance_to_target_data[sid]
                sounds.append(sound)
            except:
                # This will happen if there are synchronization errors between solr index, gaia and the database.
                # In that case sounds are set to null
                sounds.append(None)
        response_data['results'] = sounds

        if note:
            response_data['note'] = note

        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request,  *args, **kwargs):
        # This view has a post version to handle analysis file uploads
        serializer = SimilarityFileSerializer(data=request.data)
        if serializer.is_valid():
            self.analysis_file = request.FILES['analysis_file']
            return self.get(request,  *args, **kwargs)
        else:
            return Response({'detail': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class CombinedSearch(GenericAPIView):

    @classmethod
    def get_description(cls):
        return 'Search sounds in Freesound based on their tags, metadata and content-based descriptors.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#combined-search' % resources_doc_filename,
                  get_formatted_examples_for_view('CombinedSearch', 'apiv2-sound-combined-search', max=5))

    serializer_class = SimilarityFileSerializer
    analysis_file = None
    merging_strategy = 'merge_optimized'  # 'filter_both', 'merge_all'

    def get(self, request,  *args, **kwargs):
        api_logger.info(self.log_message('combined_search'))

        # Validate search form and check page 0
        search_form = SoundCombinedSearchFormAPI(request.query_params)
        if not search_form.is_valid():
            raise BadRequestException(msg='Malformed request.', resource=self)
        if (not search_form.cleaned_data['target'] and
            not search_form.cleaned_data['descriptors_filter'] and
            not self.analysis_file) \
                or (search_form.cleaned_data['query'] is None and search_form.cleaned_data['filter'] is None):
            raise BadRequestException(msg='At least one parameter from Text Search and one parameter from '
                                          'Content Search should be included in the request.', resource=self)
        if search_form.cleaned_data['target'] and search_form.cleaned_data['query']:
            raise BadRequestException(msg='Request parameters \'target\' and \'query\' can not be used at '
                                          'the same time.', resource=self)
        if search_form.cleaned_data['page'] < 1:
            raise NotFoundException(resource=self)

        # Get search results
        extra_parameters = dict()
        for key, value in request.query_params.items():
            if key.startswith('cs_'):
                extra_parameters[key] = int(value)

        analysis_file = None
        if self.analysis_file:
            analysis_file = self.analysis_file.read()
        try:
            results, count, distance_to_target_data, more_from_pack_data, note, params_for_next_page, debug_note \
                = api_search(search_form,
                             target_file=analysis_file,
                             extra_parameters=extra_parameters,
                             merging_strategy=self.merging_strategy,
                             resource=self)
        except APIException as e:
            raise e  # TODO pass correct resource parameter
        except Exception as e:
            raise ServerErrorException(msg='Unexpected error', resource=self)

        if params_for_next_page:
            extra_parameters.update(params_for_next_page)
        if request.query_params.get('debug', False):
            extra_parameters.update({'debug': 1})
        extra_parameters_string = ''
        if extra_parameters:
            for key, value in extra_parameters.items():
                extra_parameters_string += f'&{key}={str(value)}'

        response_data = dict()
        if self.analysis_file:
            response_data['target_analysis_file'] = f'{self.analysis_file._name} ({self.analysis_file._size // 1024:d} KB)'

        # Build 'more' link (only add it if we know there might be more results)
        if 'no_more_results' not in extra_parameters:
            if self.merging_strategy == 'merge_optimized':
                response_data['more'] = search_form.construct_link(reverse('apiv2-sound-combined-search'),
                                                                   include_page=False)
            else:
                num_pages = math.ceil(count / search_form.cleaned_data['page_size'])
                if search_form.cleaned_data['page'] < num_pages:
                    response_data['more'] = search_form.construct_link(reverse('apiv2-sound-combined-search'),
                                                                       page=search_form.cleaned_data['page'] + 1)
                else:
                    response_data['more'] = None
            if extra_parameters_string:
                response_data['more'] += f'{extra_parameters_string}'
        else:
            response_data['more'] = None

        # Get analysis data and serialize sound results
        ids = results
        sound_analysis_data = get_analysis_data_for_sound_ids(request, sound_ids=ids)
        # In search queries, only include audio analyers's output if requested through the fields parameter
        needs_analyzers_ouptut = 'analyzers_output' in search_form.cleaned_data.get('fields', '') or 'ac_analysis' in search_form.cleaned_data.get('fields', '')
        sounds_dict = Sound.objects.dict_ids(sound_ids=ids, include_analyzers_output=needs_analyzers_ouptut)

        sounds = []
        for i, sid in enumerate(ids):
            try:
                sound = SoundListSerializer(sounds_dict[sid], context=self.get_serializer_context(), sound_analysis_data=sound_analysis_data).data
                # Distance to target is present we add it to the serialized sound
                if distance_to_target_data:
                    sound['distance_to_target'] = distance_to_target_data[sid]
                sounds.append(sound)
            except:
                # This will happen if there are synchronization errors between solr index, gaia and the database.
                # In that case sounds are are set to null
                sounds.append(None)
        response_data['results'] = sounds

        if note:
            response_data['note'] = note

        if request.query_params.get('debug', False):
            response_data['debug_note'] = debug_note

        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request,  *args, **kwargs):
        # This view has a post version to handle analysis file uploads
        serializer = SimilarityFileSerializer(data=request.data)
        if serializer.is_valid():
            analysis_file = request.FILES['analysis_file']
            self.analysis_file = analysis_file
            return self.get(request,  *args, **kwargs)
        else:
            return Response({'detail': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


#############
# SOUND VIEWS
#############

class SoundInstance(RetrieveAPIView):

    @classmethod
    def get_description(cls):
        return 'Detailed sound information.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#sound-instance' % resources_doc_filename,
                  get_formatted_examples_for_view('SoundInstance', 'apiv2-sound-instance', max=5))

    serializer_class = SoundSerializer
    queryset = Sound.objects.filter(moderation_state="OK", processing_state="OK").annotate(analysis_state_essentia_exists=Exists(SoundAnalysis.objects.filter(analyzer=settings.FREESOUND_ESSENTIA_EXTRACTOR_NAME, analysis_status="OK", sound=OuterRef('id'))))

    def get(self, request,  *args, **kwargs):
        api_logger.info(self.log_message('sound:%i instance' % (int(kwargs['pk']))))
        return super().get(request, *args, **kwargs)


class SoundAnalysisView(GenericAPIView):  # Needs to be named SoundAnalysisView so it does not overlap with SoundAnalysis

    @classmethod
    def get_description(cls):
        return 'Sound analysis information.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#sound-analysis' % resources_doc_filename,
                  get_formatted_examples_for_view('SoundAnalysis', 'apiv2-sound-analysis', max=5))

    def get(self, request,  *args, **kwargs):
        sound_id = kwargs['pk']
        descriptors = []
        if request.query_params.get('descriptors', False):
            descriptors = request.query_params['descriptors'].split(',')
        api_logger.info(self.log_message('sound:%i analysis' % (int(sound_id))))
        response_data = get_sounds_descriptors([sound_id],
                                                descriptors,
                                                request.query_params.get('normalized', '0') == '1',
                                                only_leaf_descriptors=True)
        if response_data:
            return Response(response_data[str(sound_id)], status=status.HTTP_200_OK)
        else:
            raise NotFoundException(resource=self)


class SimilarSounds(GenericAPIView):

    @classmethod
    def get_description(cls):
        return 'Similar sounds to a given Freesound sound.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#similar-sounds' % resources_doc_filename,
                  get_formatted_examples_for_view('SimilarSounds', 'apiv2-similarity-sound', max=5))

    def get(self, request,  *args, **kwargs):

        sound_id = self.kwargs['pk']
        api_logger.info(self.log_message('sound:%i similar_sounds' % (int(sound_id))))

        # Validate search form and check page 0
        similarity_sound_form = SimilarityFormAPI(request.query_params)
        if not similarity_sound_form.is_valid():
            raise BadRequestException(msg='Malformed request.', resource=self)
        if similarity_sound_form.cleaned_data['page'] < 1:
            raise NotFoundException(resource=self)

        # Get search results
        similarity_sound_form.cleaned_data['target'] = str(sound_id)
        results, count, distance_to_target_data, more_from_pack_data, note, params_for_next_page, debug_note = \
            api_search(similarity_sound_form, resource=self)

        # Paginate results
        paginator = ApiSearchPaginator(results, count, similarity_sound_form.cleaned_data['page_size'])
        if similarity_sound_form.cleaned_data['page'] > paginator.num_pages and count != 0:
            raise NotFoundException(resource=self)
        page = paginator.page(similarity_sound_form.cleaned_data['page'])
        response_data = dict()
        response_data['count'] = paginator.count
        response_data['previous'] = None
        response_data['next'] = None
        if page['has_other_pages']:
                if page['has_previous']:
                    response_data['previous'] = similarity_sound_form.construct_link(
                        reverse('apiv2-similarity-sound', args=[sound_id]), page=page['previous_page_number'])
                if page['has_next']:
                    response_data['next'] = similarity_sound_form.construct_link(
                        reverse('apiv2-similarity-sound', args=[sound_id]), page=page['next_page_number'])

        # Get analysis data and serialize sound results
        ids = [id for id in page['object_list']]
        sound_analysis_data = get_analysis_data_for_sound_ids(request, sound_ids=ids)
        # In search queries, only include audio analyers's output if requested through the fields parameter
        needs_analyzers_ouptut = 'analyzers_output' in similarity_sound_form.cleaned_data.get('fields', '') or 'ac_analysis' in similarity_sound_form.cleaned_data.get('fields', '')
        sounds_dict = Sound.objects.dict_ids(sound_ids=ids, include_analyzers_output=needs_analyzers_ouptut)

        sounds = []
        for i, sid in enumerate(ids):
            try:
                sound = SoundListSerializer(sounds_dict[sid], context=self.get_serializer_context(), sound_analysis_data=sound_analysis_data).data
                # Distance to target is present we add it to the serialized sound
                if distance_to_target_data:
                    sound['distance_to_target'] = distance_to_target_data[sid]
                sounds.append(sound)
            except:
                # This will happen if there are synchronization errors between gaia and the database.
                # In that case sounds are are set to null
                sounds.append(None)
        response_data['results'] = sounds

        return Response(response_data, status=status.HTTP_200_OK)


class SoundComments(ListAPIView):
    serializer_class = SoundCommentsSerializer

    @classmethod
    def get_description(cls):
        return 'Sounds comments.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#sound-comments' % resources_doc_filename,
                  get_formatted_examples_for_view('SoundComments', 'apiv2-sound-comments', max=5))

    def get(self, request,  *args, **kwargs):
        api_logger.info(self.log_message('sound:%i comments' % (int(self.kwargs['pk']))))
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return Comment.objects.filter(sound_id=self.kwargs['pk'])


class DownloadSound(DownloadAPIView):

    @classmethod
    def get_description(cls):
        return 'Download a sound.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#download-sound-oauth2-required' % resources_doc_filename,
                  get_formatted_examples_for_view('DownloadSound', 'apiv2-sound-download', max=5))

    def get(self, request,  *args, **kwargs):
        sound_id = kwargs['pk']
        api_logger.info(self.log_message('sound:%i download' % (int(sound_id))))
        try:
            sound = Sound.objects.get(id=sound_id, moderation_state="OK", processing_state="OK")
        except Sound.DoesNotExist:
            raise NotFoundException(resource=self)
        sound_path, sound_friendly_filename, sound_sendfile_url = prepare_sendfile_arguments_for_sound_download(sound)
        if not os.path.exists(sound_path):
            raise NotFoundException(resource=self)
        return sendfile(sound_path, sound_friendly_filename, sound_sendfile_url)


class DownloadLink(DownloadAPIView):

    @classmethod
    def get_description(cls):
        return 'Get a url to download a sound without authentication.'

    def get(self, request, *args, **kwargs):
        sound_id = kwargs['pk']
        api_logger.info(self.log_message('sound:%i get_download_link' % (int(sound_id))))

        try:
            sound = Sound.objects.get(id=sound_id, moderation_state="OK", processing_state="OK")
        except Sound.DoesNotExist:
            raise NotFoundException(resource=self)

        download_token = jwt.encode({
            'user_id': self.user.id,
            'sound_id': sound.id,
            'client_id': self.client_id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=settings.API_DOWNLOAD_TOKEN_LIFETIME),
        }, settings.SECRET_KEY, algorithm='HS256')
        download_link = prepend_base(reverse('apiv2-download_from_token', args=[download_token]),
                                     request_is_secure=request.is_secure())
        return Response({'download_link': download_link}, status=status.HTTP_200_OK)


############
# USER VIEWS
############

class UserInstance(RetrieveAPIView):

    @classmethod
    def get_description(cls):
        return 'Detailed user information.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#user-instance' % resources_doc_filename,
                  get_formatted_examples_for_view('UserInstance', 'apiv2-user-instance', max=5))

    lookup_field = "username"
    serializer_class = UserSerializer
    queryset = User.objects.filter(is_active=True)

    def get(self, request,  *args, **kwargs):
        api_logger.info(self.log_message(f"user:{self.kwargs['username']} instance"))
        return super().get(request, *args, **kwargs)


class UserSounds(ListAPIView):
    lookup_field = "username"
    serializer_class = SoundListSerializer

    @classmethod
    def get_description(cls):
        return 'Sounds uploaded by a user.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#user-sounds' % resources_doc_filename,
                  get_formatted_examples_for_view('UserSounds', 'apiv2-user-sound-list', max=5))

    def get(self, request,  *args, **kwargs):
        api_logger.info(self.log_message(f"user:{self.kwargs['username']} sounds"))
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        try:
            user = User.objects.get(username=self.kwargs['username'], is_active=True)
        except User.DoesNotExist:
            raise NotFoundException(resource=self)
        needs_analyzers_ouptut = 'analyzers_output' in self.request.GET.get('fields', '') or 'ac_analysis' in self.request.GET.get('fields', '')
        queryset = Sound.objects.bulk_sounds_for_user(user_id=user.id, include_analyzers_output=needs_analyzers_ouptut)
        return queryset


class UserPacks(ListAPIView):
    serializer_class = PackSerializer
    queryset = Pack.objects.exclude(is_deleted=True)

    @classmethod
    def get_description(cls):
        return 'Packs created by a user.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#user-packs' % resources_doc_filename,
                  get_formatted_examples_for_view('UserPacks', 'apiv2-user-packs', max=5))

    def get(self, request,  *args, **kwargs):
        api_logger.info(self.log_message(f"user:{self.kwargs['username']} packs"))
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        try:
            User.objects.get(username=self.kwargs['username'], is_active=True)
        except User.DoesNotExist:
            raise NotFoundException(resource=self)

        queryset = Pack.objects.select_related('user')\
            .filter(user__username=self.kwargs['username']).exclude(is_deleted=True)
        return queryset


############
# PACK VIEWS
############

class PackInstance(RetrieveAPIView):
    serializer_class = PackSerializer
    queryset = Pack.objects.exclude(is_deleted=True)

    @classmethod
    def get_description(cls):
        return 'Detailed pack information.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#pack-instance' % resources_doc_filename,
                  get_formatted_examples_for_view('PackInstance', 'apiv2-pack-instance', max=5))

    def get(self, request,  *args, **kwargs):
        api_logger.info(self.log_message('pack:%i instance' % (int(kwargs['pk']))))
        return super().get(request, *args, **kwargs)


class PackSounds(ListAPIView):
    serializer_class = SoundListSerializer

    @classmethod
    def get_description(cls):
        return 'Sounds included in a pack.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#pack-sounds' % resources_doc_filename,
                  get_formatted_examples_for_view('PackSounds', 'apiv2-pack-sound-list', max=5))

    def get(self, request,  *args, **kwargs):
        api_logger.info(self.log_message('pack:%i sounds' % (int(kwargs['pk']))))
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        try:
            Pack.objects.get(id=self.kwargs['pk'], is_deleted=False)
        except Pack.DoesNotExist:
            raise NotFoundException(resource=self)
        needs_analyzers_ouptut = 'analyzers_output' in self.request.GET.get('fields', '') or 'ac_analysis' in self.request.GET.get('fields', '')  
        queryset = Sound.objects.bulk_sounds_for_pack(pack_id=self.kwargs['pk'], include_analyzers_output=needs_analyzers_ouptut)
        return queryset


class DownloadPack(DownloadAPIView):

    @classmethod
    def get_description(cls):
        return 'Download a pack.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#download-pack-oauth2-required' % resources_doc_filename,
                  get_formatted_examples_for_view('DownloadPack', 'apiv2-pack-download', max=5))

    def get(self, request,  *args, **kwargs):
        pack_id = kwargs['pk']
        api_logger.info(self.log_message('pack:%i download' % (int(pack_id))))
        try:
            pack = Pack.objects.get(id=pack_id, is_deleted=False)
        except Pack.DoesNotExist:
            raise NotFoundException(resource=self)

        sounds = pack.sounds.filter(processing_state="OK", moderation_state="OK")
        if not sounds:
            raise NotFoundException(
                msg='Sounds in pack %i have not yet been described or moderated' % int(pack_id), resource=self)

        sounds_list = pack.sounds.filter(processing_state="OK", moderation_state="OK").select_related('user', 'license')
        licenses_url = (reverse('pack-licenses', args=[pack.user.username, pack.id]))
        licenses_content = pack.get_attribution(sound_qs=sounds_list)
        return download_sounds(licenses_url, licenses_content, sounds_list)


##################
# READ WRITE VIEWS
##################


class UploadSound(WriteRequiredGenericAPIView):
    serializer_class = UploadAndDescribeAudioFileSerializer
    parser_classes = (MultiPartParser,)

    @classmethod
    def get_description(cls):
        return 'Upload an audiofile and (optionally) describe  it.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#upload-sound-oauth2-required' % resources_doc_filename,
                  get_formatted_examples_for_view('UploadSound', 'apiv2-uploads-upload', max=5))

    def post(self, request,  *args, **kwargs):
        api_logger.info(self.log_message('upload_sound'))
        serializer = UploadAndDescribeAudioFileSerializer(data=request.data)
        is_providing_description = serializer.is_providing_description(serializer.initial_data)
        if serializer.is_valid():
            audiofile = request.FILES['audiofile']
            try:
                handle_uploaded_file(self.user.id, audiofile)
            except:
                raise ServerErrorException(resource=self)

            if not settings.ALLOW_WRITE_WHEN_SESSION_BASED_AUTHENTICATION and self.auth_method_name == 'Session':
                if is_providing_description:
                    msg = 'Audio file successfully uploaded and described (now pending processing and moderation).'
                else:
                    msg = 'Audio file successfully uploaded (%i Bytes, now pending description).' % audiofile.size
                return Response(data={'detail': msg,
                                      'id': None,
                                      'note': 'Sound has not been saved in the database as browseable API is only '
                                              'for testing purposes.'},
                                status=status.HTTP_201_CREATED)
            else:
                if is_providing_description:
                    try:
                        apiv2_client = None
                        # This will always be true as long as settings.ALLOW_WRITE_WHEN_SESSION_BASED_AUTHENTICATION
                        # is False
                        if self.auth_method_name == 'OAuth2':
                            apiv2_client = request.auth.application.apiv2_client

                        sound_fields = {}
                        for key, item in serializer.data.items():
                            sound_fields[key] = item

                        filename = sound_fields.get('upload_filename', audiofile.name)
                        if not 'name' in sound_fields:
                            sound_fields['name'] = filename
                        else:
                            if not sound_fields['name']:
                                sound_fields['name'] = filename

                        directory = self.user.profile.locations()['uploads_dir']
                        sound_fields['dest_path'] = os.path.join(directory, filename)

                        if 'tags' in sound_fields:
                            sound_fields['tags'] = clean_and_split_tags(sound_fields['tags'])

                        try:
                            sound = utils.sound_upload.create_sound(
                                    self.user,
                                    sound_fields,
                                    apiv2_client=apiv2_client
                            )
                        except utils.sound_upload.NoAudioException:
                            raise OtherException('Something went wrong with accessing the file %s.'
                                                 % sound_fields['name'])
                        except utils.sound_upload.AlreadyExistsException:
                            raise OtherException("Sound could not be created because the uploaded file is "
                                                 "already part of freesound.", resource=self)
                        except utils.sound_upload.CantMoveException:
                            if settings.DEBUG:
                                msg = "File could not be copied to the correct destination."
                            else:
                                msg = "Server error."
                            raise ServerErrorException(msg=msg, resource=self)

                    except APIException as e:
                        raise e # TODO pass correct resource variable
                    except Exception as e:
                        raise ServerErrorException(msg='Unexpected error', resource=self)

                    return Response(data={'detail': 'Audio file successfully uploaded and described (now pending '
                                                    'processing and moderation).', 'id': int(sound.id) },
                                    status=status.HTTP_201_CREATED)
                else:
                    return Response(data={'filename': audiofile.name,
                                          'detail': 'Audio file successfully uploaded (%i Bytes, '
                                                    'now pending description).' % audiofile.size},
                                    status=status.HTTP_201_CREATED)
        else:
            return Response({'detail': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class PendingUploads(OauthRequiredAPIView):

    @classmethod
    def get_description(cls):
        return 'List of uploaded files which have not yet been described, processed or moderated.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#pending-uploads-oauth2-required' % resources_doc_filename,
                  get_formatted_examples_for_view('PendingUploads', 'apiv2-uploads-pending', max=5))

    def get(self, request,  *args, **kwargs):
        api_logger.info(self.log_message('pending_uploads'))

        # Look for sounds pending description
        file_structure, files = generate_tree(self.user.profile.locations()['uploads_dir'])
        pending_description = [file_instance.name for file_id, file_instance in files.items()]

        # Look for sounds pending processing
        qs = Sound.objects.filter(user=self.user).exclude(processing_state='OK').exclude(moderation_state='OK')
        pending_processing = [self.get_minimal_sound_info(sound, processing_state=True) for sound in qs]

        # Look for sounds pending moderation
        qs = Sound.objects.filter(user=self.user, processing_state='OK').exclude(moderation_state='OK')
        pending_moderation = [self.get_minimal_sound_info(sound, images=True) for sound in qs]

        data_response = dict()
        data_response['pending_description'] = pending_description
        data_response['pending_processing'] = pending_processing
        data_response['pending_moderation'] = pending_moderation

        return Response(data=data_response, status=status.HTTP_200_OK)

    def get_minimal_sound_info(self, sound, images=False, processing_state=False):
        sound_data = dict()
        for key, value in SoundSerializer(sound, context=self.get_serializer_context()).data.items():
            if key in ['id', 'name', 'tags', 'description', 'created', 'license']:
                sound_data[key] = value
            if images:
                if key == 'images':
                    sound_data[key] = value
        if processing_state:
            sound_data['processing_state'] = {
                'QU': 'Queued',
                'PE': 'Pending',
                'PR': 'Processing',
                'FA': 'Failed',
                'OK': 'Processed'
            }[str(sound.processing_state)]

        return sound_data


class DescribeSound(WriteRequiredGenericAPIView):
    serializer_class = SoundDescriptionSerializer

    @classmethod
    def get_description(cls):
        return 'Describe a previously uploaded sound.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#describe-sound-oauth2-required' % resources_doc_filename,
                  get_formatted_examples_for_view('DescribeSound', 'apiv2-uploads-describe', max=5))

    def post(self, request,  *args, **kwargs):
        api_logger.info(self.log_message('describe_sound'))
        file_structure, files = generate_tree(self.user.profile.locations()['uploads_dir'])
        filenames = [file_instance.name for file_id, file_instance in files.items()]
        serializer = SoundDescriptionSerializer(data=request.data, context={'not_yet_described_audio_files': filenames})
        if serializer.is_valid():
            if not settings.ALLOW_WRITE_WHEN_SESSION_BASED_AUTHENTICATION and self.auth_method_name == 'Session':
                return Response(data={'detail': 'Sound successfully described (now pending processing and moderation).',
                                      'id': None,
                                      'note': 'Sound has not been saved in the database as browseable API is only for '
                                              'testing purposes.'},
                                status=status.HTTP_201_CREATED)
            else:
                apiv2_client = None
                # This will always be true as long as settings.ALLOW_WRITE_WHEN_SESSION_BASED_AUTHENTICATION is False
                if self.auth_method_name == 'OAuth2':
                    apiv2_client = request.auth.client.apiv2_client
                sound_fields = serializer.data.copy()
                sound_fields['dest_path'] = os.path.join(self.user.profile.locations()['uploads_dir'],
                                                         sound_fields['upload_filename'])
                sound = utils.sound_upload.create_sound(self.user, sound_fields, apiv2_client=apiv2_client)
                return Response(data={'detail': 'Sound successfully described (now pending processing and moderation).',
                                      'id': int(sound.id)}, status=status.HTTP_201_CREATED)
        else:
            return Response({'detail': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class EditSoundDescription(WriteRequiredGenericAPIView):
    serializer_class = EditSoundDescriptionSerializer

    @classmethod
    def get_description(cls):
        return 'Edit the description of an existing sound.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#edit-sound-description-oauth2-required' % resources_doc_filename,
                  get_formatted_examples_for_view('EditSoundDescription', 'apiv2-sound-edit', max=5))

    def post(self, request,  *args, **kwargs):
        sound_id = kwargs['pk']
        # Check that sound exists
        try:
            sound = Sound.objects.get(id=sound_id, moderation_state="OK", processing_state="OK")
        except Sound.DoesNotExist:
            raise NotFoundException(resource=self)
        # Check that sound belongs to current end user
        if sound.user != self.user:
            raise UnauthorizedException(msg='Not authorized. The sound you\'re trying to edit is not owned by '
                                            'the OAuth2 logged in user.', resource=self)

        api_logger.info(self.log_message(f'sound:{sound_id} edit_description'))
        serializer = EditSoundDescriptionSerializer(data=request.data)
        if serializer.is_valid():
            if not settings.ALLOW_WRITE_WHEN_SESSION_BASED_AUTHENTICATION and self.auth_method_name == 'Session':
                return Response(data={'detail': f'Description of sound {sound_id} successfully edited.',
                                      'note': 'Description of sound %s has not been saved in the database as '
                                              'browseable API is only for testing purposes.' % sound_id},
                                status=status.HTTP_200_OK)
            else:
                if 'name' in serializer.data:
                    if serializer.data['name']:
                        sound.original_filename = serializer.data['name']
                if 'description' in serializer.data:
                    if serializer.data['description']:
                        sound.description = serializer.data['description']
                if 'tags' in serializer.data:
                    if serializer.data['tags']:
                        sound.set_tags(serializer.data['tags'])
                if 'license' in serializer.data:
                    if serializer.data['license']:
                        license = License.objects.filter(name=serializer.data['license']).order_by('-id').first()
                        if license != sound.license:
                            # Only update license and create new SoundLicenseHistory object if license has changed
                            sound.set_license(license)
                if 'geotag' in serializer.data:
                    if serializer.data['geotag']:
                        lat, lon, zoom = serializer.data['geotag'].split(',')
                        geotag = GeoTag(user=self.user,
                            lat=float(lat),
                            lon=float(lon),
                            zoom=int(zoom))
                        geotag.save()
                        sound.geotag = geotag
                if 'pack' in serializer.data:
                    if serializer.data['pack']:
                        if Pack.objects.filter(name=serializer.data['pack'], user=self.user)\
                                .exclude(is_deleted=True).exists():
                            p = Pack.objects.get(name=serializer.data['pack'], user=self.user)
                        else:
                            p, created = Pack.objects.get_or_create(user=self.user, name=serializer.data['pack'])
                        sound.pack = p
                sound.is_index_dirty = True
                sound.save()

                # Invalidate caches
                sound.invalidate_template_caches()

                return Response(data={'detail': f'Description of sound {sound_id} successfully edited.'},
                                status=status.HTTP_200_OK)
        else:
            return Response({'detail': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class BookmarkSound(WriteRequiredGenericAPIView):
    serializer_class = CreateBookmarkSerializer

    @classmethod
    def get_description(cls):
        return 'Bookmark a sound.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#bookmark-sound-oauth2-required' % resources_doc_filename,
                  get_formatted_examples_for_view('BookmarkSound', 'apiv2-user-create-bookmark', max=5))

    def post(self, request,  *args, **kwargs):
        sound_id = kwargs['pk']
        try:
            sound = Sound.objects.get(id=sound_id, moderation_state="OK", processing_state="OK")
        except Sound.DoesNotExist:
            raise NotFoundException(resource=self)
        api_logger.info(self.log_message(f'sound:{sound_id} create_bookmark'))
        serializer = CreateBookmarkSerializer(data=request.data)
        if serializer.is_valid():
            if not settings.ALLOW_WRITE_WHEN_SESSION_BASED_AUTHENTICATION and self.auth_method_name == 'Session':
                return Response(data={'detail': f'Successfully bookmarked sound {sound_id}.',
                                      'note': 'This bookmark has not been saved in the database as browseable API is '
                                              'only for testing purposes.'},
                                status=status.HTTP_201_CREATED)
            else:
                name = serializer.data.get('name', sound.original_filename)
                category_name = serializer.data.get('category', None)
                if category_name is not None:
                    category = BookmarkCategory.objects.get_or_create(user=self.user, name=category_name)
                    bookmark = Bookmark(user=self.user, sound_id=sound_id, category=category[0])
                else:
                    bookmark = Bookmark(user=self.user, sound_id=sound_id)
                bookmark.save()
                return Response(data={'detail': f'Successfully bookmarked sound {sound_id}.'},
                                status=status.HTTP_201_CREATED)
        else:
            return Response({'detail': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class RateSound(WriteRequiredGenericAPIView):
    serializer_class = CreateRatingSerializer

    @classmethod
    def get_description(cls):
        return 'Rate a sound.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#rate-sound-oauth2-required' % resources_doc_filename,
                  get_formatted_examples_for_view('RateSound', 'apiv2-user-create-rating', max=5))

    def post(self, request,  *args, **kwargs):
        sound_id = kwargs['pk']
        try:
            sound = Sound.objects.get(id=sound_id, moderation_state="OK", processing_state="OK")
        except Sound.DoesNotExist:
            raise NotFoundException(resource=self)
        api_logger.info(self.log_message(f'sound:{sound_id} create_rating'))
        serializer = CreateRatingSerializer(data=request.data)
        if serializer.is_valid():
            try:
                if not settings.ALLOW_WRITE_WHEN_SESSION_BASED_AUTHENTICATION and self.auth_method_name == 'Session':
                    return Response(data={'detail': f'Successfully rated sound {sound_id}.',
                                          'note': 'This rating has not been saved in the database as browseable API '
                                                  'is only for testing purposes.'},
                                    status=status.HTTP_201_CREATED)
                else:
                    SoundRating.objects.create(
                        user=self.user, sound_id=sound_id, rating=int(request.data['rating']) * 2)
                    Sound.objects.filter(id=sound_id).update(is_index_dirty=True)
                    return Response(data={'detail': f'Successfully rated sound {sound_id}.'},
                                    status=status.HTTP_201_CREATED)
            except IntegrityError:
                raise ConflictException(msg=f'User has already rated sound {sound_id}', resource=self)
            except:
                raise ServerErrorException(resource=self)
        else:
            return Response({'detail': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class CommentSound(WriteRequiredGenericAPIView):
    serializer_class = CreateCommentSerializer

    @classmethod
    def get_description(cls):
        return 'Add a comment to a sound.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#comment-sound-oauth2-required' % resources_doc_filename,
                  get_formatted_examples_for_view('CommentSound', 'apiv2-user-create-comment', max=5))

    def post(self, request,  *args, **kwargs):
        sound_id = kwargs['pk']
        try:
            sound = Sound.objects.get(id=sound_id, moderation_state="OK", processing_state="OK")
        except Sound.DoesNotExist:
            raise NotFoundException(resource=self)
        api_logger.info(self.log_message(f'sound:{sound_id} create_comment'))
        serializer = CreateCommentSerializer(data=request.data)
        if serializer.is_valid():
            if not settings.ALLOW_WRITE_WHEN_SESSION_BASED_AUTHENTICATION and self.auth_method_name == 'Session':
                return Response(data={'detail': f'Successfully commented sound {sound_id}.',
                                      'note': 'This comment has not been saved in the database as browseable API is '
                                              'only for testing purposes.'},
                                status=status.HTTP_201_CREATED)
            else:
                sound.add_comment(self.user, request.data['comment'])
                return Response(data={'detail': f'Successfully commented sound {sound_id}.'},
                                status=status.HTTP_201_CREATED)
        else:
            return Response({'detail': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


#############
# OTHER VIEWS
#############

@api_view(['GET'])
@throttle_classes([])
@authentication_classes([])
@permission_classes([])
def download_from_token(request, token):
    try:
        token_contents = jwt.decode(token, settings.SECRET_KEY, leeway=10)
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException(msg='This token has expired.')
    except jwt.InvalidTokenError:
        raise UnauthorizedException(msg='Invalid token.')
    try:
        sound = Sound.objects.get(id=token_contents.get('sound_id', None))
    except Sound.DoesNotExist:
        raise NotFoundException
    sound_path, sound_friendly_filename, sound_sendfile_url = prepare_sendfile_arguments_for_sound_download(sound)
    if not os.path.exists(sound_path):
        raise NotFoundException
    return sendfile(sound_path, sound_friendly_filename, sound_sendfile_url)


class Me(OauthRequiredAPIView):
    # authentication_classes = (OAuth2Authentication, SessionAuthentication)

    @classmethod
    def get_description(cls):
        return 'Get some information about the end-user logged into the api.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>.' \
               % (prepend_base('/docs/api'), '%s#me-information-about-user-authenticated-using-oauth2-oauth2-required'
                  % resources_doc_filename)

    def get(self, request,  *args, **kwargs):
        api_logger.info(self.log_message('me'))
        if self.user:
            response_data = UserSerializer(self.user, context=self.get_serializer_context()).data
            response_data.update({
                 'email': self.user.profile.get_email_for_delivery(),
                 'unique_id': self.user.id,
                 'bookmark_categories': prepend_base(reverse('apiv2-me-bookmark-categories')),
            })
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            raise ServerErrorException(resource=self)


class MeBookmarkCategories(OauthRequiredAPIView, ListAPIView):
    serializer_class = BookmarkCategorySerializer

    @classmethod
    def get_description(cls):
        return 'Bookmark categories created by the logged in user.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#me-bookmark-categories' % resources_doc_filename,
                  get_formatted_examples_for_view('MeBookmarkCategories', 'apiv2-me-bookmark-categories', max=5))

    def get(self, request,  *args, **kwargs):
        api_logger.info(self.log_message(f"user:{self.user.username} bookmark_categories"))
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if self.user:
            categories = BookmarkCategory.objects.filter(user__username=self.user.username)
            try:
                user = User.objects.get(username=self.user.username, is_active=True)
            except User.DoesNotExist:
                raise NotFoundException(resource=self)

            if Bookmark.objects.select_related("sound")\
                    .filter(user__username=self.user.username, category=None).count():
                uncategorized = BookmarkCategory(name='Uncategorized', user=user, id=0)
                return [uncategorized] + list(categories)
            else:
                return list(categories)
        else:
            raise ServerErrorException(resource=self)
        

class MeBookmarkCategorySounds(OauthRequiredAPIView, ListAPIView):
    serializer_class = SoundListSerializer

    @classmethod
    def get_description(cls):
        return 'Sounds bookmarked by a user under a particular category.' \
               '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
               % (prepend_base('/docs/api'), '%s#me-bookmark-category-sounds' % resources_doc_filename,
                  get_formatted_examples_for_view('MeBookmarkCategorySounds', 'apiv2-me-bookmark-category-sounds',
                                                  max=5))

    def get(self, request,  *args, **kwargs):
        api_logger.info(self.log_message('user:%s sounds_for_bookmark_category:%s'
                                     % (self.user.username, str(self.kwargs.get('category_id', None)))))
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if self.user:
            kwargs = dict()
            kwargs['user__username'] = self.user.username

            if 'category_id' in self.kwargs:
                if int(self.kwargs['category_id']) != 0:
                    kwargs['category__id'] = self.kwargs['category_id']
                else:
                    kwargs['category'] = None
            else:
                kwargs['category'] = None
            try:
                # TODO: this line below will not add the analysis_state_essentia_exists property to the sound objects and will
                # make the queries inneficient if the "analysis" is requested. This could be improved in the future.
                queryset = [bookmark.sound for bookmark in Bookmark.objects.select_related('sound').filter(**kwargs)]
            except:
                raise NotFoundException(resource=self)
            return queryset
        else:
            raise ServerErrorException(resource=self)

class AvailableAudioDescriptors(GenericAPIView):
    @classmethod
    def get_description(cls):
        return 'Get a list of valid audio descriptor names that can be used in content/combined search, in sound ' \
               'analysis<br>and in the analysis field of any sound list response. ' \
               'Full documentation can be found <a href="%s/%s" target="_blank">here</a>.' \
               % (prepend_base('/docs/api'), '%s#available-audio-descriptors' % resources_doc_filename)

    def get(self, request,  *args, **kwargs):
        api_logger.info(self.log_message('available_audio_descriptors'))
        try:
            descriptor_names = Similarity.get_descriptor_names()
            del descriptor_names['all']
            for key, value in descriptor_names.items():
                descriptor_names[key] = [item[1:] for item in value]  # remove initial dot from descriptor names

            return Response({
                'fixed-length': {
                    'one-dimensional': [item for item in descriptor_names['fixed-length']
                                        if item not in descriptor_names['multidimensional']],
                    'multi-dimensional': descriptor_names['multidimensional']
                },
                'variable-length': descriptor_names['variable-length']
            }, status=status.HTTP_200_OK)
        except Exception as e:
            raise ServerErrorException(resource=self)


class FreesoundApiV2Resources(GenericAPIView):
    @classmethod
    def get_description(cls):
        return 'List of resources available in the Freesound APIv2. ' \
               '<br>Full APIv2 documentation can be found <a href="%s/%s" target="_blank">here</a>.<br>Note that ' \
               'urls containing elements in brackets (<>) should be replaced with the corresponding variables.' \
               % (prepend_base('/docs/api'), 'index.html')

    def get(self, request,  *args, **kwargs):
        api_logger.info(self.log_message('api_root'))
        api_index = [
            {'Search resources': OrderedDict(sorted({
                    '01 Text Search': prepend_base(
                        reverse('apiv2-sound-text-search'), request_is_secure=request.is_secure()),
                    '02 Content Search': prepend_base(
                        reverse('apiv2-sound-content-search'), request_is_secure=request.is_secure()),
                    '03 Combined Search': prepend_base(
                        reverse('apiv2-sound-combined-search'), request_is_secure=request.is_secure()),
                }.items(), key=lambda t: t[0]))},
                {'Sound resources': OrderedDict(sorted({
                    '01 Sound instance': prepend_base(
                        reverse('apiv2-sound-instance', args=[0]).replace('0', '<sound_id>'),
                        request_is_secure=request.is_secure()),
                    '02 Similar sounds': prepend_base(
                        reverse('apiv2-similarity-sound', args=[0]).replace('0', '<sound_id>'),
                        request_is_secure=request.is_secure()),
                    '03 Sound analysis': prepend_base(
                        reverse('apiv2-sound-analysis', args=[0]).replace('0', '<sound_id>'),
                        request_is_secure=request.is_secure()),
                    '04 Sound comments': prepend_base(
                        reverse('apiv2-sound-comments', args=[0]).replace('0', '<sound_id>'),
                        request_is_secure=request.is_secure()),
                    '05 Download sound': prepend_base(
                        reverse('apiv2-sound-download', args=[0]).replace('0', '<sound_id>')),
                    '06 Bookmark sound': prepend_base(
                        reverse('apiv2-user-create-bookmark', args=[0]).replace('0', '<sound_id>')),
                    '07 Rate sound': prepend_base(
                        reverse('apiv2-user-create-rating', args=[0]).replace('0', '<sound_id>')),
                    '08 Comment sound': prepend_base(
                        reverse('apiv2-user-create-comment', args=[0]).replace('0', '<sound_id>')),
                    '09 Upload sound': prepend_base(reverse('apiv2-uploads-upload')),
                    '10 Describe sound': prepend_base(reverse('apiv2-uploads-describe')),
                    '11 Pending uploads': prepend_base(reverse('apiv2-uploads-pending')),
                    '12 Edit sound description': prepend_base(
                        reverse('apiv2-sound-edit', args=[0]).replace('0', '<sound_id>')),
                }.items(), key=lambda t: t[0]))},
                {'User resources': OrderedDict(sorted({
                    '01 User instance': prepend_base(
                        reverse('apiv2-user-instance', args=['uname']).replace('uname', '<username>'),
                        request_is_secure=request.is_secure()),
                    '02 User sounds': prepend_base(
                        reverse('apiv2-user-sound-list', args=['uname']).replace('uname', '<username>'),
                        request_is_secure=request.is_secure()),
                    '03 User packs': prepend_base(
                        reverse('apiv2-user-packs', args=['uname']).replace('uname', '<username>'),
                        request_is_secure=request.is_secure()),
                }.items(), key=lambda t: t[0]))},
                {'Pack resources': OrderedDict(sorted({
                    '01 Pack instance': prepend_base(
                        reverse('apiv2-pack-instance', args=[0]).replace('0', '<pack_id>'),
                        request_is_secure=request.is_secure()),
                    '02 Pack sounds': prepend_base(
                        reverse('apiv2-pack-sound-list', args=[0]).replace('0', '<pack_id>'),
                        request_is_secure=request.is_secure()),
                    '03 Download pack': prepend_base(
                        reverse('apiv2-pack-download', args=[0]).replace('0', '<pack_id>')),
                }.items(), key=lambda t: t[0]))},
                {'Other resources': OrderedDict(sorted({
                    '01 Me (information about user authenticated using oauth)': prepend_base(reverse('apiv2-me')),
                    '02 My bookmark categories': prepend_base(reverse('apiv2-me-bookmark-categories')),
                    '03 My bookmark category sounds': prepend_base(
                        reverse('apiv2-me-bookmark-category-sounds', args=[0]).replace('0', '<category_id>'),
                        request_is_secure=request.is_secure()),
                    '04 Available audio descriptors': prepend_base(reverse('apiv2-available-descriptors')),
                }.items(), key=lambda t: t[0]))},
            ]

        # Yaml format can not represent ordered dicts, so turn ordered dict to dict if these formats are requested
        if request.accepted_renderer.format in ['yaml']:
            for element in api_index:
                for key, ordered_dict in element.items():
                    element[key] = dict(ordered_dict)

        # Xml format seems to have problems with white spaces and numbers in dict keys...
        def key_to_valid_xml(key):
            # Remove white spaces, parenthesis, and add underscore in the beggining
            return '_' + key.replace(' ', '_').replace('(', '').replace(')', '')

        if request.accepted_renderer.format == 'xml':
            aux_api_index = list()
            for element in api_index:
                aux_dict_a = dict()
                for key_a, ordered_dict in element.items():
                    aux_dict_b = dict()
                    for key_b, value in ordered_dict.items():
                        aux_dict_b[key_to_valid_xml(key_b)] = value
                    aux_dict_a[key_to_valid_xml(key_a)] = aux_dict_b
                aux_api_index.append(aux_dict_a)
            api_index = aux_api_index

        return Response(api_index)


@api_view(['GET'])
@authentication_classes([OAuth2Authentication, TokenAuthentication, SessionAuthentication])
def invalid_url(request):
    """View for returning "Invalid url" 400 responses"""
    raise InvalidUrlException(request=request)


@login_required
def create_apiv2_key(request):
    """View for applying for an apikey"""

    if request.method == 'POST':
        form = ApiV2ClientForm(request.POST)
        if form.is_valid():
            api_client = ApiV2Client()
            api_client.user = request.user
            api_client.description = form.cleaned_data['description']
            api_client.name = form.cleaned_data['name']
            api_client.url = form.cleaned_data['url']
            api_client.redirect_uri = form.cleaned_data['redirect_uri']
            api_client.accepted_tos = form.cleaned_data['accepted_tos']
            api_client.save()
            form = ApiV2ClientForm()
            api_logger.info('new_credential <> (ApiV2 Auth:%s Dev:%s User:%s Client:%s)' %
                            (None, request.user.username, None, api_client.client_id))
    else:
        form = ApiV2ClientForm()

    user_credentials = request.user.apiv2_client.all()

    use_https_in_callback = True
    if settings.DEBUG:
        use_https_in_callback = False
    fs_callback_url = prepend_base(reverse('permission-granted'), use_https=use_https_in_callback)

    tvars = {
        'user': request.user,
        'form': form,
        'user_credentials': user_credentials,
        'fs_callback_url': fs_callback_url,
    }
    return render(request, 'api/credentials.html', tvars)


@login_required
def edit_api_credential(request, key):
    client = None
    try:
        client = ApiV2Client.objects.get(key=key)
    except ApiV2Client.DoesNotExist:
        pass

    if not client:
        raise Http404

    if request.method == 'POST':
        form = ApiV2ClientForm(request.POST)
        if form.is_valid():
            client.name = form.cleaned_data['name']
            client.url = form.cleaned_data['url']
            client.redirect_uri = form.cleaned_data['redirect_uri']
            client.description = form.cleaned_data['description']
            client.accepted_tos = form.cleaned_data['accepted_tos']
            client.save()
            messages.add_message(request, messages.INFO, f"Credentials with name {client.name} have been updated.")
            return HttpResponseRedirect(reverse("apiv2-apply"))
    else:
        form = ApiV2ClientForm(initial={'name': client.name,
                                        'url': client.url,
                                        'redirect_uri': client.redirect_uri,
                                        'description': client.description,
                                        'accepted_tos': client.accepted_tos
                                        })
    use_https_in_callback = True
    if settings.DEBUG:
        use_https_in_callback = False
    fs_callback_url = prepend_base(reverse('permission-granted'), use_https=use_https_in_callback)

    tvars = {
        'client': client,
        'form': form,
        'fs_callback_url': fs_callback_url,
    }
    return render(request, 'api/edit_api_credential.html', tvars)


@login_required
def monitor_api_credential(request, key):
    try:
        client = ApiV2Client.objects.get(key=key)
        level = int(client.throttling_level)
        limit_rates = settings.APIV2_BASIC_THROTTLING_RATES_PER_LEVELS[level]
        try:
            day_limit = limit_rates[1].split('/')[0]
        except IndexError:
            day_limit = 0
        n_days = int(request.GET.get('n_days', 30))
        usage_history = client.get_usage_history(n_days_back=n_days)
        last_year = datetime.datetime.now().year - 1
        tvars = {
            'n_days': n_days,
            'n_days_options': [
                (30, '1 month'),
                (93, '3 months'),
                (182, '6 months'),
                (365, '1 year')
            ], 'client': client,
            'data': json.dumps([(str(date), count) for date, count in usage_history]),
            'total_in_range': sum([count for _, count in usage_history]),
            'total_in_range_above_5000': sum([count - 5000 for _, count in usage_history if count > 5000]),
            'total_previous_year_above_5000': client.get_usage_history_total(year=last_year, discard_per_day=5000),
            'last_year': last_year,
            'limit': day_limit
        }
        return render(request, 'api/monitor_api_credential.html', tvars)
    except ApiV2Client.DoesNotExist:
        raise Http404


@login_required
def delete_api_credential(request, key):
    name = ""
    try:
        client = ApiV2Client.objects.get(key=key)
        name = client.name
        client.delete()
    except ApiV2Client.DoesNotExist:
        pass
    messages.add_message(request, messages.INFO, f"Credentials with name {name} have been deleted.")
    return HttpResponseRedirect(reverse("apiv2-apply"))


@login_required
def granted_permissions(request):
    user = request.user
    tokens_raw = AccessToken.objects.select_related('application').filter(user=user).order_by('-expires')
    tokens = []
    token_names = []

    # If settings.OAUTH_SINGLE_ACCESS_TOKEN is set to false it is possible that one single user have more than one
    # active access token per application. In that case we only show the one that expires later (and all are removed
    # if permissions revoked). If settings.OAUTH_SINGLE_ACCESS_TOKEN is set to true we don't need the token name check
    # below because there can only be one access token per client-user pair. Nevertheless the code below works in
    # both cases.

    for token in tokens_raw:
        if token.application.apiv2_client.name not in token_names:
            td = (token.expires - datetime.datetime.today())
            seconds_to_expiration_date = td.total_seconds()
            tokens.append({
                'client_name': token.application.apiv2_client.name,
                'expiration_date': token.expires,
                'expired': seconds_to_expiration_date < 0,
                'client_id': token.application.apiv2_client.client_id,
                'developer': token.application.apiv2_client.user.username,
            })
            token_names.append(token.application.apiv2_client.name)

    grants_pending_access_token_request_raw = \
        Grant.objects.select_related('application').filter(user=user).order_by('-expires')
    grants = []
    grant_and_token_names = token_names[:]
    for grant in grants_pending_access_token_request_raw:
        if grant.application.apiv2_client.name not in grant_and_token_names:
            td = (grant.expires - datetime.datetime.today())
            seconds_to_expiration_date = td.total_seconds()
            if seconds_to_expiration_date > 0:
                grants.append({
                    'client_name': grant.application.apiv2_client.name,
                    'expiration_date': grant.expires,
                    'expired': seconds_to_expiration_date < 0,
                    'client_id': grant.application.apiv2_client.client_id,
                    'developer': grant.application.apiv2_client.user.username,
                })
                grant_and_token_names.append(grant.application.apiv2_client.name)

    return render(request, 'accounts/manage_api_permissions.html', {
        'user': request.user,
        'tokens': tokens,
        'grants': grants,
        'show_expiration_date': False,
        'activePage': 'api', 
    })


@login_required
def revoke_permission(request, client_id):
    user = request.user
    tokens = AccessToken.objects.filter(user=user, application__client_id=client_id)
    for token in tokens:
        token.delete()

    grants = Grant.objects.filter(user=user, application__client_id=client_id)
    for grant in grants:
        grant.delete()

    messages.add_message(request, messages.INFO, "Permission has been successfully revoked")
    return HttpResponseRedirect(reverse("access-tokens"))


@login_required
def permission_granted(request):
    user = request.user
    code = request.GET.get('code', None)
    app_name = None
    try:
        grant = Grant.objects.get(user=user, code=code)
        app_name = grant.application.apiv2_client.name
    except Grant.DoesNotExist:
        grant = None
    logout_next = request.GET.get('original_path', None)
    if logout_next:
        logout_next = quote(logout_next)
    else:
        logout_next = reverse('api-login')
    return render(request, 'oauth2_provider/app_authorized.html',
        {'code': code, 'app_name': app_name, 'logout_next': logout_next})
