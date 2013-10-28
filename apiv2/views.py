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

from sounds.models import Sound, Pack
from search.forms import SoundSearchFormAPI
from django.contrib.auth.models import User
from apiv2.serializers import SoundSerializer, SoundListSerializer, UserSerializer, UploadAudioFileSerializer, PackSerializer, SoundDescriptionSerializer, UploadAndDescribeAudioFileSerializer, prepend_base
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes
from apiv2.authentication import OAuth2Authentication, TokenAuthentication, SessionAuthentication
from forms import ApiV2ClientForm
from models import ApiV2Client
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext
from utils import GenericAPIView, ListAPIView, RetrieveAPIView, WriteRequiredGenericAPIView, get_analysis_data_for_queryset_or_sound_ids, create_sound_object
from exceptions import NotFoundException, InvalidUrlException, ServerErrorException
from rest_framework.exceptions import ParseError
import settings
import logging
from django.http import HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
import datetime
from provider.oauth2.models import AccessToken, Grant
from api.models import ApiKey
from api.forms import ApiKeyForm
from django.contrib import messages
from accounts.views import handle_uploaded_file
from freesound.utils.filesystem import generate_tree
from freesound.utils.search.solr import Solr, SolrQuery, SolrException, SolrResponseInterpreter, SolrResponseInterpreterPaginator
from piston.utils import rc
from search.views import search_prepare_query
import os


logger = logging.getLogger("api")


@api_view(('GET',))
def api_root(request, format=None):
    '''
    Main docs
    '''

    return Response({
        #'upload': reverse('apiv2-uploads-upload'),
    })


#############
# SOUND VIEWS
#############


class SoundInstance(RetrieveAPIView):
    """
    Detailed sound information.
    TODO: proper doccumentation.
    """
    serializer_class = SoundSerializer
    queryset = Sound.objects.filter(moderation_state="OK", processing_state="OK")

    def get(self, request,  *args, **kwargs):
        logger.info("TODO: proper logging")
        return super(SoundInstance, self).get(request, *args, **kwargs)


class SoundSearch(GenericAPIView):
    """
    Sound search.
    TODO: proper doccumentation.
    """

    def get(self, request,  *args, **kwargs):
        search_form = SoundSearchFormAPI(request.GET)
        if not search_form.is_valid():
            raise ParseError

        solr = Solr(settings.SOLR_URL)
        query = search_prepare_query(search_form.cleaned_data['query'],
                                     search_form.cleaned_data['filter'],
                                     search_form.cleaned_data['sort'],
                                     search_form.cleaned_data['page'],
                                     search_form.cleaned_data['page_size'],
                                     grouping=search_form.cleaned_data['group_by_pack'])

        try:
            results = SolrResponseInterpreter(solr.select(unicode(query)))
            paginator = SolrResponseInterpreterPaginator(results, search_form.cleaned_data['page_size'])
            page = paginator.page(search_form.cleaned_data['page'])
            get_analysis_data_for_queryset_or_sound_ids(self, sound_ids=[object['id'] for object in page['object_list']])
            sounds = []
            for object in page['object_list']:
                try:
                    sound = SoundListSerializer(Sound.objects.select_related('user').get(id=object['id']), context=self.get_serializer_context()).data
                    if 'more_from_pack' in object.keys():
                        if object['more_from_pack'] > 0:
                            sound['more_from_same_pack'] = self.__construct_more_from_pack_link(search_form, object['pack_name'])
                            sound['n_from_same_pack'] = object['more_from_pack']
                    sounds.append(sound)
                except:  # This will happen if there are synchronization errors between solr index and the database. In that case sounds are ommited and 'count' might become inacurate
                    sounds.append(None)
            response_data = {'count': paginator.count}

            # construct previous and next urls
            if page['has_other_pages']:
                if not page['has_previous']:
                    response_data['previous'] = None
                else:
                    response_data['previous'] = self.__construct_pagination_link(search_form, page['previous_page_number'])

                if not page['has_next']:
                    response_data['next'] = None
                else:
                    response_data['next'] = self.__construct_pagination_link(search_form, page['next_page_number'])

            response_data['results'] = sounds

        except SolrException:
                raise ServerErrorException

        return Response(response_data, status=status.HTTP_200_OK)

    def __construct_pagination_link(self, search_form, page_number):
        return prepend_base(reverse('apiv2-sound-search') +
                            '?query=%s' \
                            '&filter=%s' \
                            '&sort=%s' \
                            '&page=%s' \
                            '&page_size=%s' \
                            '&group_by_pack=%s' \
                            '&fields=%s' \
                            '&descriptors=%s' \
                            '&normalized=%s' % (
                                  search_form.cleaned_data['query'],
                                  search_form.cleaned_data['filter'],
                                  search_form.original_url_sort_value,
                                  page_number,
                                  search_form.cleaned_data['page_size'],
                                  search_form.cleaned_data['group_by_pack'],
                                  search_form.cleaned_data['fields'],
                                  search_form.cleaned_data['descriptors'],
                                  search_form.cleaned_data['normalized']
                            ))

    def __construct_more_from_pack_link(self, search_form, pack_name):
        return prepend_base(reverse('apiv2-sound-search') +
                            '?query=%s' \
                            '&filter=pack:%s' \
                            '&sort=%s' \
                            '&page_size=%s' \
                            '&fields=%s' \
                            '&descriptors=%s' \
                            '&normalized=%s' % (
                                  search_form.cleaned_data['query'],
                                  pack_name,
                                  search_form.original_url_sort_value,
                                  search_form.cleaned_data['page_size'],
                                  search_form.cleaned_data['fields'],
                                  search_form.cleaned_data['descriptors'],
                                  search_form.cleaned_data['normalized']
                            ))


############
# USER VIEWS
############


class UserInstance(RetrieveAPIView):
    """
    Detailed user information.
    TODO: proper doccumentation.
    """
    lookup_field = "username"
    serializer_class = UserSerializer
    queryset = User.objects.filter(is_active=True)

    def get(self, request,  *args, **kwargs):
        logger.info("TODO: proper logging")
        return super(UserInstance, self).get(request, *args, **kwargs)


class UserSoundList(ListAPIView):
    """
    List of sounds uploaded by user.
    TODO: proper doccumentation.
    """
    lookup_field = "username"
    serializer_class = SoundListSerializer

    def get(self, request,  *args, **kwargs):
        logger.info("TODO: proper logging")
        return super(UserSoundList, self).get(request, *args, **kwargs)

    def get_queryset(self):
        try:
            User.objects.get(username=self.kwargs['username'], is_active=True)
        except User.DoesNotExist:
            raise NotFoundException()

        queryset = Sound.objects.select_related('user').filter(moderation_state="OK",
                                                               processing_state="OK",
                                                               user__username=self.kwargs['username'])
        get_analysis_data_for_queryset_or_sound_ids(self, queryset=queryset)

        return queryset


############
# PACK VIEWS
############


class PackInstance(RetrieveAPIView):
    """
    Detailed pack information.
    TODO: proper doccumentation.
    """
    serializer_class = PackSerializer
    queryset = Pack.objects.all()

    def get(self, request,  *args, **kwargs):
        logger.info("TODO: proper logging")
        return super(PackInstance, self).get(request, *args, **kwargs)


class PackSoundList(ListAPIView):
    """
    List of sounds in a pack.
    TODO: proper doccumentation.
    """
    serializer_class = SoundListSerializer

    def get(self, request,  *args, **kwargs):
        logger.info("TODO: proper logging")
        return super(PackSoundList, self).get(request, *args, **kwargs)

    def get_queryset(self):
        try:
            Pack.objects.get(id=self.kwargs['pk'])
        except Pack.DoesNotExist:
            raise NotFoundException()

        queryset = Sound.objects.select_related('pack').filter(moderation_state="OK",
                                                               processing_state="OK",
                                                               pack__id=self.kwargs['pk'])
        get_analysis_data_for_queryset_or_sound_ids(self, queryset=queryset)

        return queryset


##############
# UPLOAD VIEWS
##############


class UploadAudioFile(WriteRequiredGenericAPIView):
    """
    Upload a sound (without description)
    TODO: proper doccumentation.
    """
    serializer_class = UploadAudioFileSerializer

    def post(self, request,  *args, **kwargs):
        logger.info("TODO: proper logging")
        serializer = UploadAudioFileSerializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            audiofile = request.FILES['audiofile']
            try:
                handle_uploaded_file(self.user.id, audiofile)
            except:
                raise ServerErrorException

            return Response(data={'filename': audiofile.name, 'details': 'File successfully uploaded (%i)' % audiofile.size}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotYetDescribedUploadedAudioFiles(WriteRequiredGenericAPIView):
    """
    List uploaded audio files which have not been yes described
    TODO: proper doccumentation.
    """

    def get(self, request,  *args, **kwargs):
        logger.info("TODO: proper logging")
        file_structure, files = generate_tree(os.path.join(settings.UPLOADS_PATH, str(self.user.id)))
        filenames = [file_instance.name for file_id, file_instance in files.items()]
        return Response(data={'filenames': filenames}, status=status.HTTP_200_OK)


class DescribeAudioFile(WriteRequiredGenericAPIView):
    """
    Describe a previously uploaded audio file (audio file is identified by its filename which must be a post param)
    TODO: proper doccumentation.
    """
    serializer_class = SoundDescriptionSerializer

    def post(self, request,  *args, **kwargs):
        logger.info("TODO: proper logging")
        file_structure, files = generate_tree(os.path.join(settings.UPLOADS_PATH, str(self.user.id)))
        filenames = [file_instance.name for file_id, file_instance in files.items()]
        serializer = SoundDescriptionSerializer(data=request.DATA, context={'not_yet_described_audio_files': filenames})
        if serializer.is_valid():
            sound = create_sound_object(self.user, request.DATA)
            return Response(data={'details': 'Sound successfully described', 'uri': prepend_base(reverse('apiv2-sound-instance', args=[sound.id]))}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UploadAndDescribeAudioFile(WriteRequiredGenericAPIView):
    """
    Upload a sound and describe it (without description)
    TODO: proper doccumentation.
    """
    serializer_class = UploadAndDescribeAudioFileSerializer

    def post(self, request,  *args, **kwargs):
        logger.info("TODO: proper logging")
        serializer = UploadAndDescribeAudioFileSerializer(data=request.DATA, files=request.FILES)
        if serializer.is_valid():
            audiofile = request.FILES['audiofile']
            try:
                handle_uploaded_file(self.user.id, audiofile)
            except:
                raise ServerErrorException
            request.DATA['upload_filename'] = request.FILES['audiofile'].name
            sound = create_sound_object(self.user, request.DATA)
            return Response(data={'details': 'Audio file successfully uploaded and described', 'uri': prepend_base(reverse('apiv2-sound-instance', args=[sound.id])) }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



#############
# OTHER VIEWS
#############


### View for returning "Invalid url" 400 responses
@api_view(['GET'])
@authentication_classes([OAuth2Authentication, TokenAuthentication, SessionAuthentication])
def return_invalid_url(request):
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
    else:
        form = ApiV2ClientForm()

    if settings.APIV2KEYS_ALLOWED_FOR_APIV1:
        user_credentials = list(request.user.apiv2_client.all()) + list(request.user.api_keys.all())
    else:
        user_credentials = request.user.apiv2_client.all()
    fs_callback_url = request.build_absolute_uri(reverse('permission-granted'))

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

    fs_callback_url = request.build_absolute_uri(reverse('permission-granted'))
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
            tokens.append({
                'client_name': token.client.apiv2_client.name,
                'expiration_date': token.expires,
                'expired': (token.expires - datetime.datetime.today()).total_seconds() < 0,
                'scope': token.client.apiv2_client.get_scope_display,
                'client_id': token.client.apiv2_client.client_id,
            })
        token_names.append(token.client.apiv2_client.name)

    return render_to_response('api/manage_permissions.html',
                              {'user': request.user, 'tokens': tokens},
                              context_instance=RequestContext(request))


### View to revoke permissions granted to an application
@login_required
def revoke_permission(request, client_id):
    user = request.user
    tokens = AccessToken.objects.filter(user=user, client__client_id=client_id)
    for token in tokens:
        token.delete()

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

    return render_to_response(template,
                              {'code': code, 'app_name': app_name},
                              context_instance=RequestContext(request))


