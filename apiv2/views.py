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


from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.exceptions import ParseError
from provider.oauth2.models import AccessToken, Grant
from apiv2.serializers import *
from apiv2.authentication import OAuth2Authentication, TokenAuthentication, SessionAuthentication
from utils import GenericAPIView, ListAPIView, RetrieveAPIView, WriteRequiredGenericAPIView, OauthRequiredAPIView, get_analysis_data_for_queryset_or_sound_ids, create_sound_object, api_search, ApiSearchPaginator, get_sounds_descriptors, prepend_base,  get_formatted_examples_for_view
from exceptions import *
from forms import *
from models import ApiV2Client
from api.models import ApiKey
from bookmarks.models import Bookmark, BookmarkCategory
from api.forms import ApiKeyForm
from accounts.views import handle_uploaded_file
from search.views import search_prepare_query, search_prepare_sort
from freesound.utils.filesystem import generate_tree
from freesound.utils.search.solr import Solr, SolrException, SolrResponseInterpreter, SolrResponseInterpreterPaginator
from freesound.utils.nginxsendfile import sendfile
from django.db import IntegrityError
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.core.urlresolvers import reverse
try:
    from collections import OrderedDict
except:
    from freesound.utils.ordered_dict import OrderedDict
from urllib import unquote, quote
import settings
import logging
import datetime
import os

logger = logging.getLogger("api")
docs_base_url = prepend_base('/docs/api')
resources_doc_filename = 'resources_apiv2.html'


####################################
# SEARCH AND SIMILARITY SEARCH VIEWS
####################################

class TextSearch(GenericAPIView):

    __doc__ = 'Search sounds in Freesound based on their tags and other metadata.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#text-search' % resources_doc_filename,
                 get_formatted_examples_for_view('TextSearch', 'apiv2-sound-search', max=5))

    def get(self, request,  *args, **kwargs):
        logger.info(self.log_message('search'))

        # Validate search form and check page 0
        search_form = SoundTextSearchFormAPI(request.QUERY_PARAMS)
        if not search_form.is_valid():
            raise ParseError
        if not search_form.cleaned_data['query'] and not search_form.cleaned_data['filter']:
           raise InvalidUrlException(msg='At lesast one request parameter from Text Search should be included in the request.')
        if search_form.cleaned_data['page'] < 1:
            raise NotFoundException

        # Get search results
        try:
            results, count, distance_to_target_data, more_from_pack_data, note = api_search(search_form)
        except Exception, e:
            raise e

        # Paginate results
        paginator = ApiSearchPaginator(results, count, search_form.cleaned_data['page_size'])
        if search_form.cleaned_data['page'] > paginator.num_pages and count != 0:
            raise NotFoundException
        page = paginator.page(search_form.cleaned_data['page'])
        response_data = dict()
        response_data['count'] = paginator.count
        response_data['previous'] = None
        response_data['next'] = None
        if page['has_other_pages']:
                if page['has_previous']:
                    response_data['previous'] = search_form.construct_link(reverse('apiv2-sound-text-search'), page=page['previous_page_number'])
                if page['has_next']:
                    response_data['next'] = search_form.construct_link(reverse('apiv2-sound-text-search'), page=page['next_page_number'])

        # Get analysis data and serialize sound results
        ids = [id for id in page['object_list']]
        get_analysis_data_for_queryset_or_sound_ids(self, sound_ids=ids)
        qs = Sound.objects.select_related('user', 'pack', 'license').filter(id__in=ids)
        qs_sound_objects = dict()
        for sound_object in qs:
            qs_sound_objects[sound_object.id] = sound_object
        sounds = []
        for i, sid in enumerate(ids):
            try:
                sound = SoundListSerializer(qs_sound_objects[sid], context=self.get_serializer_context()).data
                if more_from_pack_data:
                    if more_from_pack_data[sid][0]:
                        sound['more_from_same_pack'] = search_form.construct_link(reverse('apiv2-sound-text-search'), page=1, filter='grouping_pack:"%i_%s"' % (int(more_from_pack_data[sid][1]), more_from_pack_data[sid][2]), group_by_pack='0')
                        sound['n_from_same_pack'] = more_from_pack_data[sid][0] + 1  # we add one as is the sound itself
                sounds.append(sound)
            except:
                # This will happen if there are synchronization errors between solr index, gaia and the database.
                # In that case sounds are are set to null
                sounds.append(None)
        response_data['results'] = sounds

        if note:
            response_data['note'] = note

        return Response(response_data, status=status.HTTP_200_OK)


class ContentSearch(GenericAPIView):

    __doc__ = 'Search sounds in Freesound based on their content descriptors.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#content-search' % resources_doc_filename,
                 get_formatted_examples_for_view('ContentSearch', 'apiv2-sound-content-search', max=5))

    serializer_class = SimilarityFileSerializer
    analysis_file = None

    def get(self, request,  *args, **kwargs):
        logger.info(self.log_message('content_search'))

        # Validate search form and check page 0
        search_form = SoundContentSearchFormAPI(request.QUERY_PARAMS)
        if not search_form.is_valid():
            raise ParseError
        if not search_form.cleaned_data['target'] and not search_form.cleaned_data['descriptors_filter'] and not self.analysis_file:
           raise InvalidUrlException(msg='At lesast one parameter from Content Search should be included in the request.')
        if search_form.cleaned_data['page'] < 1:
                raise NotFoundException

        # Get search results
        analysis_file = None
        if self.analysis_file:
            analysis_file = self.analysis_file.read()
        try:
            results, count, distance_to_target_data, more_from_pack_data, note = api_search(search_form, target_file=analysis_file)
        except Exception, e:
            raise e

        # Paginate results
        paginator = ApiSearchPaginator(results, count, search_form.cleaned_data['page_size'])
        if search_form.cleaned_data['page'] > paginator.num_pages and count != 0:
            raise NotFoundException
        page = paginator.page(search_form.cleaned_data['page'])
        response_data = dict()
        if self.analysis_file:
            response_data['target_analysis_file'] = '%s (%i KB)' % (self.analysis_file._name, self.analysis_file._size/1024)
        response_data['count'] = paginator.count
        response_data['previous'] = None
        response_data['next'] = None
        if page['has_other_pages']:
                if page['has_previous']:
                    response_data['previous'] = search_form.construct_link(reverse('apiv2-sound-content-search'), page=page['previous_page_number'])
                if page['has_next']:
                    response_data['next'] = search_form.construct_link(reverse('apiv2-sound-content-search'), page=page['next_page_number'])

        # Get analysis data and serialize sound results
        ids = [id for id in page['object_list']]
        get_analysis_data_for_queryset_or_sound_ids(self, sound_ids=ids)
        qs = Sound.objects.select_related('user', 'pack', 'license').filter(id__in=ids)
        qs_sound_objects = dict()
        for sound_object in qs:
            qs_sound_objects[sound_object.id] = sound_object
        sounds = []
        for i, sid in enumerate(ids):
            try:
                sound = SoundListSerializer(qs_sound_objects[sid], context=self.get_serializer_context()).data
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

        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request,  *args, **kwargs):
        # This view has a post version to handle analysis file uploads
        serializer = SimilarityFileSerializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            analysis_file = request.FILES['analysis_file']
            self.analysis_file = analysis_file
            return self.get(request,  *args, **kwargs)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CombinedSearch(GenericAPIView):

    __doc__ = 'Search sounds in Freesound based on their tags, metadata and content-based descriptors.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#combined-search' % resources_doc_filename,
                 get_formatted_examples_for_view('CombinedSearch', 'apiv2-sound-combined-search', max=5))

    serializer_class = SimilarityFileSerializer
    analysis_file = None

    def get(self, request,  *args, **kwargs):
        logger.info(self.log_message('combined_search'))

        # Validate search form and check page 0
        search_form = SoundCombinedSearchFormAPI(request.QUERY_PARAMS)
        if not search_form.is_valid():
            raise ParseError
        if (not search_form.cleaned_data['target'] and not search_form.cleaned_data['descriptors_filter'] and not self.analysis_file) or (not search_form.cleaned_data['query'] and not search_form.cleaned_data['filter']):
           raise InvalidUrlException(msg='At lesast one parameter from Text Search and one parameter from Content Search should be included in the request.')
        if search_form.cleaned_data['page'] < 1:
                raise NotFoundException

        # Get search results
        max_repeat = int(request.QUERY_PARAMS.get('max_repeat', 0)) # Max repeat is an additional parameter to tweak performance in combined search
        max_solr_filter_ids = int(request.QUERY_PARAMS.get('max_solr_filter_ids', 0)) # Max repeat is an additional parameter to tweak performance in combined search
        analysis_file = None
        if self.analysis_file:
            analysis_file = self.analysis_file.read()
        try:
            results, count, distance_to_target_data, more_from_pack_data, note = api_search(search_form, target_file=analysis_file, max_repeat=max_repeat, max_solr_filter_ids=max_solr_filter_ids)
        except Exception, e:
            raise e

        # Paginate results
        paginator = ApiSearchPaginator(results, count, search_form.cleaned_data['page_size'])
        if search_form.cleaned_data['page'] > paginator.num_pages and count != 0:
            raise NotFoundException
        page = paginator.page(search_form.cleaned_data['page'])
        response_data = dict()
        if self.analysis_file:
            response_data['target_analysis_file'] = '%s (%i KB)' % (self.analysis_file._name, self.analysis_file._size/1024)
        response_data['count'] = paginator.count
        response_data['previous'] = None
        response_data['next'] = None
        if page['has_other_pages']:
                if page['has_previous']:
                    response_data['previous'] = search_form.construct_link(reverse('apiv2-sound-combined-search'), page=page['previous_page_number'])
                    if max_repeat:
                        response_data['previous'] += '&max_repeat=%i' % max_repeat
                if page['has_next']:
                    response_data['next'] = search_form.construct_link(reverse('apiv2-sound-combined-search'), page=page['next_page_number'])
                    if max_repeat:
                        response_data['next'] += '&max_repeat=%i' % max_repeat

        # Get analysis data and serialize sound results
        ids = [id for id in page['object_list']]
        get_analysis_data_for_queryset_or_sound_ids(self, sound_ids=ids)
        qs = Sound.objects.select_related('user', 'pack', 'license').filter(id__in=ids)
        qs_sound_objects = dict()
        for sound_object in qs:
            qs_sound_objects[sound_object.id] = sound_object
        sounds = []
        for i, sid in enumerate(ids):
            try:
                sound = SoundListSerializer(qs_sound_objects[sid], context=self.get_serializer_context()).data
                # Distance to target is present we add it to the serialized sound
                if distance_to_target_data:
                    sound['distance_to_target'] = distance_to_target_data[sid]
                if more_from_pack_data:
                    if more_from_pack_data[sid][0]:
                        sound['more_from_same_pack'] = search_form.construct_link(reverse('apiv2-sound-combined-search'), page=1, filter='grouping_pack:"%i_%s"' % (int(more_from_pack_data[sid][1]), more_from_pack_data[sid][2]), group_by_pack='0')
                        sound['n_from_same_pack'] = None #more_from_pack_data[sid][0] + 1  # we add one as is the sound itself
                sounds.append(sound)
            except:
                # This will happen if there are synchronization errors between solr index, gaia and the database.
                # In that case sounds are are set to null
                sounds.append(None)
        response_data['results'] = sounds

        if note:
            response_data['note'] = note

        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request,  *args, **kwargs):
        # This view has a post version to handle analysis file uploads
        serializer = SimilarityFileSerializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            analysis_file = request.FILES['analysis_file']
            self.analysis_file = analysis_file
            return self.get(request,  *args, **kwargs)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#############
# SOUND VIEWS
#############

class SoundInstance(RetrieveAPIView):
    __doc__ = 'Detailed sound information.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#sound-instance' % resources_doc_filename,
                 get_formatted_examples_for_view('SoundInstance', 'apiv2-sound-instance', max=5))

    serializer_class = SoundSerializer
    queryset = Sound.objects.filter(moderation_state="OK", processing_state="OK")

    def get(self, request,  *args, **kwargs):
        logger.info(self.log_message('sound:%i instance' % (int(kwargs['pk']))))
        return super(SoundInstance, self).get(request, *args, **kwargs)


class SoundAnalysis(GenericAPIView):
    __doc__ = 'Sound analysis information.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#sound-analysis' % resources_doc_filename,
                 get_formatted_examples_for_view('SoundAnalysis', 'apiv2-sound-analysis', max=5))

    def get(self, request,  *args, **kwargs):
        sound_id = kwargs['pk']
        descriptors = []
        if request.QUERY_PARAMS.get('descriptors', False):
            descriptors = request.QUERY_PARAMS['descriptors'].split(',')
        logger.info(self.log_message('sound:%i analysis' % (int(sound_id))))
        response_data = get_sounds_descriptors([sound_id],
                                                descriptors,
                                                request.QUERY_PARAMS.get('normalized', '0') == '1',
                                                only_leaf_descriptors=True)
        if response_data:
            return Response(response_data[str(sound_id)], status=status.HTTP_200_OK)
        else:
            raise NotFoundException


class SimilarSounds(GenericAPIView):
    __doc__ = 'Similar sounds to a given Freesound sound.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#similar-sounds' % resources_doc_filename,
                 get_formatted_examples_for_view('SimilarSounds', 'apiv2-similarity-sound', max=5))

    def get(self, request,  *args, **kwargs):

        sound_id = self.kwargs['pk']
        logger.info(self.log_message('sound:%i similar_sounds' % (int(sound_id))))

        # Validate search form and check page 0
        similarity_sound_form = SimilarityFormAPI(request.QUERY_PARAMS)
        if not similarity_sound_form.is_valid():
            raise ParseError
        if similarity_sound_form.cleaned_data['page'] < 1:
            raise NotFoundException

        # Get search results
        similarity_sound_form.cleaned_data['target'] = str(sound_id)
        results, count, distance_to_target_data, more_from_pack_data, note = api_search(similarity_sound_form)

        # Paginate results
        paginator = ApiSearchPaginator(results, count, similarity_sound_form.cleaned_data['page_size'])
        if similarity_sound_form.cleaned_data['page'] > paginator.num_pages and count != 0:
            raise NotFoundException
        page = paginator.page(similarity_sound_form.cleaned_data['page'])
        response_data = dict()
        response_data['count'] = paginator.count
        response_data['previous'] = None
        response_data['next'] = None
        if page['has_other_pages']:
                if page['has_previous']:
                    response_data['previous'] = similarity_sound_form.construct_link(reverse('apiv2-similarity-sound', args=[sound_id]), page=page['previous_page_number'])
                if page['has_next']:
                    response_data['next'] = similarity_sound_form.construct_link(reverse('apiv2-similarity-sound', args=[sound_id]), page=page['next_page_number'])

        # Get analysis data and serialize sound results
        ids = [id for id in page['object_list']]
        get_analysis_data_for_queryset_or_sound_ids(self, sound_ids=ids)
        qs = Sound.objects.select_related('user', 'pack', 'license').filter(id__in=ids)
        qs_sound_objects = dict()
        for sound_object in qs:
            qs_sound_objects[sound_object.id] = sound_object
        sounds = []
        for i, sid in enumerate(ids):
            try:
                sound = SoundListSerializer(qs_sound_objects[sid], context=self.get_serializer_context()).data
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
    __doc__ = 'Sounds comments.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#sound-comments' % resources_doc_filename,
                 get_formatted_examples_for_view('SoundComments', 'apiv2-sound-comments', max=5))
    serializer_class = SoundCommentsSerializer

    def get(self, request,  *args, **kwargs):
        logger.info(self.log_message('sound:%i comments' % (int(self.kwargs['pk']))))
        return super(SoundComments, self).get(request, *args, **kwargs)

    def get_queryset(self):
        return Comment.objects.filter(object_id=self.kwargs['pk'])


class DownloadSound(OauthRequiredAPIView):
    __doc__ = 'Download a sound.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#download-sound' % resources_doc_filename,
                 get_formatted_examples_for_view('DownloadSound', 'apiv2-sound-download', max=5))

    def get(self, request,  *args, **kwargs):
        sound_id = kwargs['pk']
        logger.info(self.log_message('sound:%i download' % (int(sound_id))))
        try:
            sound = Sound.objects.get(id=sound_id, moderation_state="OK", processing_state="OK")
        except Sound.DoesNotExist:
            raise NotFoundException

        if not os.path.exists(sound.locations('path')):
            raise NotFoundException

        return sendfile(sound.locations("path"), sound.friendly_filename(), sound.locations("sendfile_url"))


############
# USER VIEWS
############

class UserInstance(RetrieveAPIView):
    __doc__ = 'Detailed user information.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#user-instance' % resources_doc_filename,
                 get_formatted_examples_for_view('UserInstance', 'apiv2-user-instance', max=5))

    lookup_field = "username"
    serializer_class = UserSerializer
    queryset = User.objects.filter(is_active=True)

    def get(self, request,  *args, **kwargs):
        logger.info(self.log_message('user:%s instance' % (self.kwargs['username'])))
        return super(UserInstance, self).get(request, *args, **kwargs)


class UserSounds(ListAPIView):
    __doc__ = 'Sounds uploaded by a user.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#user-sounds' % resources_doc_filename,
                 get_formatted_examples_for_view('UserSounds', 'apiv2-user-sound-list', max=5))

    lookup_field = "username"
    serializer_class = SoundListSerializer

    def get(self, request,  *args, **kwargs):
        logger.info(self.log_message('user:%s sounds' % (self.kwargs['username'])))
        return super(UserSounds, self).get(request, *args, **kwargs)

    def get_queryset(self):
        try:
            User.objects.get(username=self.kwargs['username'], is_active=True)
        except User.DoesNotExist:
            raise NotFoundException

        queryset = Sound.objects.select_related('user', 'pack', 'license').filter(moderation_state="OK",
                                                                                  processing_state="OK",
                                                                                  user__username=self.kwargs['username'])
        get_analysis_data_for_queryset_or_sound_ids(self, queryset=queryset)
        return queryset


class UserPacks (ListAPIView):
    __doc__ = 'Packs created by a user.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#user-packs' % resources_doc_filename,
                 get_formatted_examples_for_view('UserPacks', 'apiv2-user-packs', max=5))

    serializer_class = PackSerializer
    queryset = Pack.objects.all()

    def get(self, request,  *args, **kwargs):
        logger.info(self.log_message('user:%s packs' % (self.kwargs['username'])))
        return super(UserPacks, self).get(request, *args, **kwargs)

    def get_queryset(self):
        try:
            User.objects.get(username=self.kwargs['username'], is_active=True)
        except User.DoesNotExist:
            raise NotFoundException

        queryset = Pack.objects.select_related('user').filter(user__username=self.kwargs['username'])
        return queryset


class UserBookmarkCategories(ListAPIView):
    __doc__ = 'Bookmark categories created by a user.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#user-bookmark-categories' % resources_doc_filename,
                 get_formatted_examples_for_view('UserBookmarkCategories', 'apiv2-user-bookmark-categories', max=5))

    serializer_class = BookmarkCategorySerializer

    def get(self, request,  *args, **kwargs):
        logger.info(self.log_message('user:%s bookmark_categories' % (self.kwargs['username'])))
        return super(UserBookmarkCategories, self).get(request, *args, **kwargs)

    def get_queryset(self):
        categories = BookmarkCategory.objects.filter(user__username=self.kwargs['username'])
        try:
            user = User.objects.get(username=self.kwargs['username'], is_active=True)
        except User.DoesNotExist:
            raise NotFoundException

        if Bookmark.objects.select_related("sound").filter(user__username=self.kwargs['username'], category=None).count():
            uncategorized = BookmarkCategory(name='Uncategorized', user=user, id=0)
            return [uncategorized] + list(categories)
        else:
            return list(categories)


class UserBookmarkCategorySounds(ListAPIView):
    __doc__ = 'Sounds bookmarked by a user under a particular category.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#user-bookmark-category-sounds' % resources_doc_filename,
                 get_formatted_examples_for_view('UserBookmarkCategorySounds', 'apiv2-user-bookmark-category-sounds', max=5))

    serializer_class = SoundListSerializer

    def get(self, request,  *args, **kwargs):
        logger.info(self.log_message('user:%s sounds_for_bookmark_category:%s' % (self.kwargs['username'], str(self.kwargs.get('category_id', None)))))
        return super(UserBookmarkCategorySounds, self).get(request, *args, **kwargs)

    def get_queryset(self):

        kwargs = dict()
        kwargs['user__username'] = self.kwargs['username']

        if 'category_id' in self.kwargs:
            if int(self.kwargs['category_id']) != 0:
                kwargs['category__id'] = self.kwargs['category_id']
            else:
                kwargs['category'] = None
        else:
            kwargs['category'] = None

        try:
            queryset = [bookmark.sound for bookmark in Bookmark.objects.select_related('sound').filter(**kwargs)]
        except:
            raise NotFoundException

        get_analysis_data_for_queryset_or_sound_ids(self, queryset=queryset)
        #[bookmark.sound for bookmark in Bookmark.objects.select_related("sound").filter(user__username=self.kwargs['username'],category=None)]

        return queryset


############
# PACK VIEWS
############

class PackInstance(RetrieveAPIView):
    __doc__ = 'Detailed pack information.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#pack-instance' % resources_doc_filename,
                 get_formatted_examples_for_view('PackInstance', 'apiv2-pack-instance', max=5))

    serializer_class = PackSerializer
    queryset = Pack.objects.all()

    def get(self, request,  *args, **kwargs):
        logger.info(self.log_message('pack:%i instance' % (int(kwargs['pk']))))
        return super(PackInstance, self).get(request, *args, **kwargs)


class PackSounds(ListAPIView):
    __doc__ = 'Sounds included in a pack.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#pack-sounds' % resources_doc_filename,
                 get_formatted_examples_for_view('PackSounds', 'apiv2-pack-sound-list', max=5))

    serializer_class = SoundListSerializer

    def get(self, request,  *args, **kwargs):
        logger.info(self.log_message('pack:%i sounds' % (int(kwargs['pk']))))
        return super(PackSounds, self).get(request, *args, **kwargs)

    def get_queryset(self):
        try:
            Pack.objects.get(id=self.kwargs['pk'])
        except Pack.DoesNotExist:
            raise NotFoundException

        queryset = Sound.objects.select_related('user', 'pack', 'license').filter(moderation_state="OK",
                                                                                  processing_state="OK",
                                                                                  pack__id=self.kwargs['pk'])
        get_analysis_data_for_queryset_or_sound_ids(self, queryset=queryset)
        return queryset


class DownloadPack(OauthRequiredAPIView):
    __doc__ = 'Download a pack.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#download-pack' % resources_doc_filename,
                 get_formatted_examples_for_view('DownloadPack', 'apiv2-pack-download', max=5))


    def get(self, request,  *args, **kwargs):
        pack_id = kwargs['pk']
        logger.info(self.log_message('pack:%i download' % (int(pack_id))))
        try:
            pack = Pack.objects.get(id=pack_id)
        except Pack.DoesNotExist:
            raise NotFoundException

        sounds = pack.sound_set.filter(processing_state="OK", moderation_state="OK")
        if not sounds:
            raise NotFoundException(msg='Sounds in pack %i have not yet been described or moderated' % int(pack_id))

        try:
            filelist = "%s %i %s %s\r\n" % (pack.license_crc,
                                            os.stat(pack.locations('license_path')).st_size,
                                            pack.locations('license_url'),
                                            "_readme_and_license.txt")
        except:
            raise ServerErrorException

        for sound in sounds:
            url = sound.locations("sendfile_url")
            name = sound.friendly_filename()
            if sound.crc == '':
                continue
            filelist += "%s %i %s %s\r\n" % (sound.crc, sound.filesize, url, name)
        response = HttpResponse(filelist, content_type="text/plain")
        response['X-Archive-Files'] = 'zip'
        return response


##################
# READ WRITE VIEWS
##################

class UploadSound(WriteRequiredGenericAPIView):
    __doc__ = 'Upload a sound (only upload the file, without description/metadata).' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#upload-sound' % resources_doc_filename,
                 get_formatted_examples_for_view('UploadSound', 'apiv2-uploads-upload', max=5))

    serializer_class = UploadAudioFileSerializer

    def post(self, request,  *args, **kwargs):
        logger.info(self.log_message('uploading_sound'))
        serializer = UploadAudioFileSerializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            audiofile = request.FILES['audiofile']
            
            if not settings.ALLOW_WRITE_WHEN_SESSION_BASED_AUTHENTICATION and self.auth_method_name == 'Session':
                return Response(data={'filename': audiofile.name,
                                      'details': 'File successfully uploaded (%i)' % audiofile.size,
                                      'note': 'File has not been saved as browseable API is only for testing purposes.'},
                                status=status.HTTP_201_CREATED)
            else:
                try:
                    handle_uploaded_file(self.user.id, audiofile)
                except:
                    raise ServerErrorException
                return Response(data={'filename': audiofile.name, 'details': 'File successfully uploaded (%i)' % audiofile.size}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotYetDescribedUploadedSounds(OauthRequiredAPIView):
    __doc__ = 'List of uploaded files which have not yet been described.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#uploads-pending-description' % resources_doc_filename,
                 get_formatted_examples_for_view('NotYetDescribedUploadedSounds', 'apiv2-uploads-not-described', max=5))

    def get(self, request,  *args, **kwargs):
        logger.info(self.log_message('not_yet_described_uploaded_sounds'))
        file_structure, files = generate_tree(os.path.join(settings.UPLOADS_PATH, str(self.user.id)))
        filenames = [file_instance.name for file_id, file_instance in files.items()]
        return Response(data={'filenames': filenames}, status=status.HTTP_200_OK)


class UploadedAndDescribedSoundsPendingModeration(OauthRequiredAPIView):
    __doc__ = 'List of uploaded files which have already been descriebd and are procesing or awaiting moderation in Freesound.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#uploadeds_pending_moderation' % resources_doc_filename,
                 get_formatted_examples_for_view('UploadedAndDescribedSoundsPendingModeration', 'apiv2-uploads-not-moderated', max=5))

    def get(self, request,  *args, **kwargs):
        logger.info(self.log_message('uploadeds_pending_moderation'))
        sounds_pending_processing = Sound.objects.filter(user=self.user, moderation_state='PE').exclude(processing_state='OK')
        sounds_pending_moderation = Sound.objects.filter(user=self.user, processing_state='OK', moderation_state='PE')

        data_response = dict()
        data_response['sounds pending processing'] = [self.get_minimal_sound_info(sound) for sound in sounds_pending_processing]
        data_response['sounds pending moderation'] = [self.get_minimal_sound_info(sound, images=True) for sound in sounds_pending_moderation]

        return Response(data=data_response, status=status.HTTP_200_OK)

    def get_minimal_sound_info(self, sound, images=False):
        sound_data = dict()
        for key, value in SoundSerializer(sound, context=self.get_serializer_context()).data.items():
            if key in ['name', 'tags', 'description', 'created', 'license']:
                sound_data[key] = value
            if images:
                if key == 'images':
                    sound_data[key] = value
        return sound_data


class DescribeSound(WriteRequiredGenericAPIView):
    __doc__ = 'Describe a previously uploaded sound.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#describe-sound' % resources_doc_filename,
                 get_formatted_examples_for_view('DescribeSound', 'apiv2-uploads-describe', max=5))

    serializer_class = SoundDescriptionSerializer

    def post(self, request,  *args, **kwargs):
        logger.info(self.log_message('describe_sound'))
        file_structure, files = generate_tree(os.path.join(settings.UPLOADS_PATH, str(self.user.id)))
        filenames = [file_instance.name for file_id, file_instance in files.items()]
        serializer = SoundDescriptionSerializer(data=request.DATA, context={'not_yet_described_audio_files': filenames})
        if serializer.is_valid():
            if not settings.ALLOW_WRITE_WHEN_SESSION_BASED_AUTHENTICATION and self.auth_method_name == 'Session':
                return Response(data={'details': 'Sound successfully described (now pending moderation)',
                                      'uri': None,
                                      'note': 'Sound has not been saved in the database as browseable API is only for testing purposes.'},
                                status=status.HTTP_201_CREATED)
            else:
                sound = create_sound_object(self.user, request.DATA)
                return Response(data={'details': 'Sound successfully described (now pending moderation)', 'uri': prepend_base(reverse('apiv2-sound-instance', args=[sound.id]))}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UploadAndDescribeSound(WriteRequiredGenericAPIView):
    __doc__ = 'Upload and describe (add metadata) a sound file.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#upload-and-describe-sound' % resources_doc_filename,
                 get_formatted_examples_for_view('UploadAndDescribeSound', 'apiv2-uploads-upload-and-describe', max=5))

    serializer_class = UploadAndDescribeAudioFileSerializer

    def post(self, request,  *args, **kwargs):
        logger.info(self.log_message('upload_and_describe_sound'))
        serializer = UploadAndDescribeAudioFileSerializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            audiofile = request.FILES['audiofile']
            try:
                handle_uploaded_file(self.user.id, audiofile)
            except:
                raise ServerErrorException
            request.DATA['upload_filename'] = request.FILES['audiofile'].name

            if not settings.ALLOW_WRITE_WHEN_SESSION_BASED_AUTHENTICATION and self.auth_method_name == 'Session':
                return Response(data={'details': 'Audio file successfully uploaded and described (now pending moderation)',
                                      'uri': None,
                                      'note': 'Sound has not been saved in the database as browseable API is only for testing purposes.'},
                                status=status.HTTP_201_CREATED)
            else:
                sound = create_sound_object(self.user, request.DATA)
                return Response(data={'details': 'Audio file successfully uploaded and described (now pending moderation)', 'uri': prepend_base(reverse('apiv2-sound-instance', args=[sound.id])) }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BookmarkSound(WriteRequiredGenericAPIView):
    __doc__ = 'Bookmark a sound.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#bookmark-sound' % resources_doc_filename,
                 get_formatted_examples_for_view('BookmarkSound', 'apiv2-user-create-bookmark', max=5))

    serializer_class = CreateBookmarkSerializer

    def post(self, request,  *args, **kwargs):
        sound_id = kwargs['pk']
        logger.info(self.log_message('sound:%s create_bookmark' % sound_id))
        serializer = CreateBookmarkSerializer(data=request.DATA)
        if serializer.is_valid():
            if not settings.ALLOW_WRITE_WHEN_SESSION_BASED_AUTHENTICATION and self.auth_method_name == 'Session':
                return Response(data={'details': 'Successfully bookmarked sound %s' % sound_id,
                                      'note': 'This bookmark has not been saved in the database as browseable API is only for testing purposes.'},
                                status=status.HTTP_201_CREATED)
            else:
                if ('category' in request.DATA):
                    category = BookmarkCategory.objects.get_or_create(user=self.user, name=request.DATA['category'])
                    bookmark = Bookmark(user=self.user, name=request.DATA['name'], sound_id=sound_id, category=category[0])
                else:
                    bookmark = Bookmark(user=self.user, name=request.DATA['name'], sound_id=sound_id)
                bookmark.save()
                return Response(data={'details': 'Successfully bookmarked sound %s' % sound_id}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RateSound(WriteRequiredGenericAPIView):
    __doc__ = 'Rate a sound.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#rate-sound' % resources_doc_filename,
                 get_formatted_examples_for_view('RateSound', 'apiv2-user-create-rating', max=5))

    serializer_class = CreateRatingSerializer

    def post(self, request,  *args, **kwargs):
        sound_id = kwargs['pk']
        logger.info(self.log_message('sound:%s create_rating' % sound_id))
        serializer = CreateRatingSerializer(data=request.DATA)
        if serializer.is_valid():
            try:
                if not settings.ALLOW_WRITE_WHEN_SESSION_BASED_AUTHENTICATION and self.auth_method_name == 'Session':
                    return Response(data={'details': 'Successfully rated sound %s' % sound_id,
                                          'note': 'This rating has not been saved in the database as browseable API is only for testing purposes.'},
                                    status=status.HTTP_201_CREATED)
                else:
                    Rating.objects.create(user=self.user, object_id=sound_id, content_type=ContentType.objects.get(id=20), rating=int(request.DATA['rating'])*2)
                    return Response(data={'details': 'Successfully rated sound %s' % sound_id}, status=status.HTTP_201_CREATED)
            except IntegrityError:
                raise InvalidUrlException(msg='User has already rated sound %s' % sound_id)
            except:
                raise ServerErrorException
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentSound(WriteRequiredGenericAPIView):
    __doc__ = 'Add a comment to a sound.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>. %s' \
              % (docs_base_url, '%s#comment-sound' % resources_doc_filename,
                 get_formatted_examples_for_view('CommentSound', 'apiv2-user-create-comment', max=5))

    serializer_class = CreateCommentSerializer

    def post(self, request,  *args, **kwargs):
        sound_id = kwargs['pk']
        logger.info(self.log_message('sound:%s create_comment' % sound_id))
        serializer = CreateCommentSerializer(data=request.DATA)
        if serializer.is_valid():
            if not settings.ALLOW_WRITE_WHEN_SESSION_BASED_AUTHENTICATION and self.auth_method_name == 'Session':
                return Response(data={'details': 'Successfully commented sound %s' % sound_id,
                                      'note': 'This comment has not been saved in the database as browseable API is only for testing purposes.'},
                                status=status.HTTP_201_CREATED)
            else:
                comment = Comment.objects.create(user=self.user, object_id=sound_id, content_type=ContentType.objects.get(id=20), comment=request.DATA['comment'])
                if comment.content_type == ContentType.objects.get_for_model(Sound):
                    sound = comment.content_object
                    sound.num_comments = sound.num_comments + 1
                    sound.save()
                return Response(data={'details': 'Successfully commented sound %s' % sound_id}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#############
# OTHER VIEWS
#############

### Me View
class Me(OauthRequiredAPIView):
    __doc__ = 'Get some information about the end-user logged into the api.' \
              '<br>Full documentation can be found <a href="%s/%s" target="_blank">here</a>.' \
              % (docs_base_url, '%s#me' % resources_doc_filename)

    #authentication_classes = (OAuth2Authentication, SessionAuthentication)

    def get(self, request,  *args, **kwargs):
        logger.info(self.log_message('me'))
        if self.user:
            response_data = UserSerializer(self.user, context=self.get_serializer_context()).data
            response_data.update({
                 'email': self.user.email,
            })
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            raise ServerErrorException


### Root view
class FreesoundApiV2Resources(GenericAPIView):
    __doc__ = 'List of resources available in the Freesound API V2. ' \
              '<br>Full documentation API can be found <a href="%s/%s" target="_blank">here</a>.' \
              '<br>Note that urls containing elements in brackets (<>) should be replaced with the corresponding variables.' \
              % (docs_base_url, 'index.html')

    #authentication_classes = (OAuth2Authentication, TokenAuthentication, SessionAuthentication)

    def get(self, request,  *args, **kwargs):

        logger.info(self.log_message('api_root'))
        return Response([
            {'Search resources': OrderedDict(sorted(dict({
                    '01 Text Search': prepend_base(reverse('apiv2-sound-text-search'), request_is_secure=request.using_https),
                    '02 Content Search': prepend_base(reverse('apiv2-sound-content-search'), request_is_secure=request.using_https),
                    '03 Combined Search': prepend_base(reverse('apiv2-sound-combined-search'), request_is_secure=request.using_https),
                }).items(), key=lambda t: t[0]))},
                {'Sound resources': OrderedDict(sorted(dict({
                    '01 Sound instance': prepend_base(reverse('apiv2-sound-instance', args=[0]).replace('0', '<sound_id>'), request_is_secure=request.using_https),
                    '02 Similar sounds': prepend_base(reverse('apiv2-similarity-sound', args=[0]).replace('0', '<sound_id>'), request_is_secure=request.using_https),
                    '03 Sound analysis': prepend_base(reverse('apiv2-sound-analysis', args=[0]).replace('0', '<sound_id>'), request_is_secure=request.using_https),
                    '04 Sound comments': prepend_base(reverse('apiv2-sound-comments', args=[0]).replace('0', '<sound_id>'), request_is_secure=request.using_https),
                    '05 Download sound': prepend_base(reverse('apiv2-sound-download', args=[0]).replace('0', '<sound_id>')),
                    '06 Bookmark sound': prepend_base(reverse('apiv2-user-create-bookmark', args=[0]).replace('0', '<sound_id>')),
                    '07 Rate sound': prepend_base(reverse('apiv2-user-create-rating', args=[0]).replace('0', '<sound_id>')),
                    '08 Comment sound': prepend_base(reverse('apiv2-user-create-comment', args=[0]).replace('0', '<sound_id>')),
                    '09 Upload sound': prepend_base(reverse('apiv2-uploads-upload')),
                    '10 Describe uploaded sound': prepend_base(reverse('apiv2-uploads-describe')),
                    '11 Uploaded sounds pending description': prepend_base(reverse('apiv2-uploads-not-described')),
                    '12 Upload and describe sound': prepend_base(reverse('apiv2-uploads-upload-and-describe')),
                    '13 Uploaded and described sounds pending moderation': prepend_base(reverse('apiv2-uploads-not-moderated')),
                }).items(), key=lambda t: t[0]))},
                {'User resources': OrderedDict(sorted(dict({
                    '01 User instance': prepend_base(reverse('apiv2-user-instance', args=['uname']).replace('uname', '<username>'), request_is_secure=request.using_https),
                    '02 User sounds': prepend_base(reverse('apiv2-user-sound-list', args=['uname']).replace('uname', '<username>'), request_is_secure=request.using_https),
                    '03 User packs': prepend_base(reverse('apiv2-user-packs', args=['uname']).replace('uname', '<username>'), request_is_secure=request.using_https),
                    '04 User bookmark categories': prepend_base(reverse('apiv2-user-bookmark-categories', args=['uname']).replace('uname', '<username>'), request_is_secure=request.using_https),
                    '05 User bookmark category sounds': prepend_base(reverse('apiv2-user-bookmark-category-sounds', args=['uname', 0]).replace('0', '<category_id>').replace('uname', '<username>'), request_is_secure=request.using_https),
                    '06 Me (information about user authenticated using oauth)': prepend_base(reverse('apiv2-me')),
                }).items(), key=lambda t: t[0]))},
                {'Pack resources': OrderedDict(sorted(dict({
                    '01 Pack instance': prepend_base(reverse('apiv2-pack-instance', args=[0]).replace('0', '<pack_id>'), request_is_secure=request.using_https),
                    '02 Pack sounds': prepend_base(reverse('apiv2-pack-sound-list', args=[0]).replace('0', '<pack_id>'), request_is_secure=request.using_https),
                    '03 Download pack': prepend_base(reverse('apiv2-pack-download', args=[0]).replace('0', '<pack_id>')),
                }).items(), key=lambda t: t[0]))},
            ])


### View for returning "Invalid url" 400 responses
@api_view(['GET'])
@authentication_classes([OAuth2Authentication, TokenAuthentication, SessionAuthentication])
def invalid_url(request):
    raise InvalidUrlException


### View for applying for an apikey
@login_required
def create_apiv2_key(request):

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
            logger.info('%s <> (ApiV2 Auth:%s Dev:%s User:%s Client:%s)' % ('new_credential', None, request.user.username, None, api_client.client_id))
    else:
        form = ApiV2ClientForm()

    if settings.APIV2KEYS_ALLOWED_FOR_APIV1:
        user_credentials = list(request.user.apiv2_client.all()) + list(request.user.api_keys.all())
    else:
        user_credentials = request.user.apiv2_client.all()

    use_https_in_callback = True
    if settings.DEBUG:
        use_https_in_callback = False
    fs_callback_url = prepend_base(reverse('permission-granted'), use_https=use_https_in_callback)  #request.build_absolute_uri(reverse('permission-granted'))


    return render_to_response('api/apply_key_apiv2.html',
                              {'user': request.user,
                               'form': form,
                               'user_credentials': user_credentials,
                               'combined_apiv1_and_apiv2': settings.APIV2KEYS_ALLOWED_FOR_APIV1,
                               'fs_callback_url': fs_callback_url,
                               }, context_instance=RequestContext(request))


### View for editing client (works both for apiv2 and apiv1)
@login_required
def edit_api_credential(request, key):
    client = None
    try:
        client = ApiV2Client.objects.get(key=key)
    except ApiV2Client.DoesNotExist:
        pass

    try:
        client = ApiKey.objects.get(key=key)
    except ApiKey.DoesNotExist:
        pass

    if not client:
        raise Http404

    if request.method == 'POST':
        if client.version == 'V2':
            form = ApiV2ClientForm(request.POST)
            if form.is_valid():
                client.name = form.cleaned_data['name']
                client.url = form.cleaned_data['url']
                client.redirect_uri = form.cleaned_data['redirect_uri']
                client.description = form.cleaned_data['description']
                client.accepted_tos = form.cleaned_data['accepted_tos']
                client.save()
                messages.add_message(request, messages.INFO, "Credentials with name %s have been updated." % client.name)
                return HttpResponseRedirect(reverse("apiv2-apply"))
        elif client.version == 'V1':
            form = ApiKeyForm(request.POST)
            if form.is_valid():
                client.name = form.cleaned_data['name']
                client.url = form.cleaned_data['url']
                client.description = form.cleaned_data['description']
                client.accepted_tos = form.cleaned_data['accepted_tos']
                client.save()
                messages.add_message(request, messages.INFO, "Credentials with name %s have been updated." % client.name)
                return HttpResponseRedirect(reverse("apiv2-apply"))
    else:
        if client.version == 'V2':
            form = ApiV2ClientForm(initial={'name': client.name,
                                            'url': client.url,
                                            'redirect_uri': client.redirect_uri,
                                            'description': client.description,
                                            'accepted_tos': client.accepted_tos
                                            })
        elif client.version == 'V1':
            form = ApiKeyForm(initial={'name': client.name,
                                        'url': client.url,
                                        'description': client.description,
                                        'accepted_tos': client.accepted_tos
                                        })

    use_https_in_callback = True
    if settings.DEBUG:
        use_https_in_callback = False
    fs_callback_url = prepend_base(reverse('permission-granted'), use_https=use_https_in_callback)
    return render_to_response('api/edit_api_credential.html',
                              {'client': client,
                               'form': form,
                               'fs_callback_url': fs_callback_url,
                               }, context_instance=RequestContext(request))


### View for deleting api clients (works both for apiv2 and apiv1)
@login_required
def delete_api_credential(request, key):
    name = ""

    try:
        client = ApiV2Client.objects.get(key=key)
        name = client.name
        client.delete()
    except ApiV2Client.DoesNotExist:
        pass

    try:
        client = ApiKey.objects.get(key=key)
        name = client.name
        client.delete()
    except ApiKey.DoesNotExist:
        pass

    messages.add_message(request, messages.INFO, "Credentials with name %s have been deleted." % name)
    return HttpResponseRedirect(reverse("apiv2-apply"))


### View for managing permissions granted to apps
@login_required
def granted_permissions(request):
    user = request.user
    tokens_raw = AccessToken.objects.select_related('client').filter(user=user).order_by('-expires')
    tokens = []
    token_names = []

    # If settings.OAUTH_SINGLE_ACCESS_TOKEN is set to false it is possible that one single user have more than one active
    # access token per application. In that case we only show the one that expires later (and all are removed if permissions
    # revoked). If settings.OAUTH_SINGLE_ACCESS_TOKEN is set to true we don't need the token name check below because
    # there can only be one access token per client-user pair. Nevertheless the code below works in both cases.

    for token in tokens_raw:
        if not token.client.apiv2_client.name in token_names:
            td = (token.expires - datetime.datetime.today())
            seconds_to_expiration_date = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
            tokens.append({
                'client_name': token.client.apiv2_client.name,
                'expiration_date': token.expires,
                'expired': seconds_to_expiration_date < 0,
                'scope': token.client.apiv2_client.get_scope_display,
                'client_id': token.client.apiv2_client.client_id,
                'developer': token.client.apiv2_client.user.username,
            })
            token_names.append(token.client.apiv2_client.name)

    grants_pending_access_token_request_raw = Grant.objects.select_related('client').filter(user=user).order_by('-expires')
    grants = []
    grant_and_token_names = token_names[:]
    for grant in grants_pending_access_token_request_raw:
        if not grant.client.apiv2_client.name in grant_and_token_names:
            td = (grant.expires - datetime.datetime.today())
            seconds_to_expiration_date = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6
            if seconds_to_expiration_date > 0:
                grants.append({
                    'client_name': grant.client.apiv2_client.name,
                    'expiration_date': grant.expires,
                    'expired': seconds_to_expiration_date < 0,
                    'scope': grant.client.apiv2_client.get_scope_display,
                    'client_id': grant.client.apiv2_client.client_id,
                    'developer': grant.client.apiv2_client.user.username,
                })
                grant_and_token_names.append(grant.client.apiv2_client.name)

    return render_to_response('api/manage_permissions.html',
                              {'user': request.user, 'tokens': tokens, 'grants': grants, 'show_expiration_date': False},
                              context_instance=RequestContext(request))


### View to revoke permissions granted to an application
@login_required
def revoke_permission(request, client_id):
    user = request.user
    tokens = AccessToken.objects.filter(user=user, client__client_id=client_id)
    for token in tokens:
        token.delete()

    grants = Grant.objects.filter(user=user, client__client_id=client_id)
    for grant in grants:
        grant.delete()

    return HttpResponseRedirect(reverse("access-tokens"))


### View to show grant code (pin code) if application does not support redirection
@login_required
def permission_granted(request):
    user = request.user
    code = request.GET.get('code', None)
    app_name = None
    try:
        grant = Grant.objects.get(user=user, code=code)
        app_name = grant.client.apiv2_client.name
    except:
        grant = None

    if settings.USE_MINIMAL_TEMPLATES_FOR_OAUTH:
        template = 'api/minimal_app_authorized.html'
    else:
        template = 'api/app_authorized.html'

    logout_next = quote(request.GET.get('original_path', None))
    if not logout_next:
        logout_next = reverse('api-login')

    return render_to_response(template,
                              {'code': code, 'app_name': app_name, 'logout_next': logout_next},
                              context_instance=RequestContext(request))


