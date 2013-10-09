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

from sounds.models import Sound
from django.contrib.auth.models import User
from apiv2.serializers import SoundSerializer, SoundListSerializer, UserSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import generics
from apiv2.authentication import OAuth2Authentication, TokenAuthentication, SessionAuthentication
from forms import ApiV2ClientForm
from models import ApiV2Client
from django.contrib.auth.decorators import login_required
from django.shortcuts import render_to_response
from django.template import RequestContext
from utils import get_authentication_details_form_request
import settings
import logging


logger = logging.getLogger("api")


@api_view(('GET',))
def api_root(request, format=None):
    return Response({
        #'sounds': reverse('apiv2-sound-list', request=request, format=format),
    })


class SoundDetail(generics.RetrieveAPIView):
    """
    Detailed sound information.
    """
    authentication_classes = (OAuth2Authentication, TokenAuthentication,)
    queryset = Sound.objects.filter(moderation_state="OK", processing_state="OK")
    serializer_class = SoundSerializer


class UserDetail(generics.RetrieveAPIView):
    """
    Detailed user information.
    """
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer


class UserSoundList(generics.ListAPIView):
    """
    List of sounds uploaded by user.
    """
    authentication_classes = (OAuth2Authentication, TokenAuthentication, SessionAuthentication)
    serializer_class = SoundListSerializer

    def get(self, request,  *args, **kwargs):
        print "Auth method: %s, Developer: %s, End user: %s" % get_authentication_details_form_request(request)
        logger.info("Test log")
        return super(UserSoundList, self).get(request, *args, **kwargs)

    def get_queryset(self):
        return Sound.objects.select_related('user').filter(moderation_state="OK",
                                                           processing_state="OK",
                                                           user__id=self.kwargs['pk'])


### View for applying for an apikey

@login_required
def create_apiv2_key(request):
    user_credentials = None
    if request.method == 'POST':
        form = ApiV2ClientForm(request.POST)
        if form.is_valid():
            db_api_key = ApiV2Client()
            db_api_key.user = request.user
            db_api_key.description = form.cleaned_data['description']
            db_api_key.name = form.cleaned_data['name']
            db_api_key.url = form.cleaned_data['url']
            db_api_key.redirect_uri = form.cleaned_data['redirect_uri']
            db_api_key.accepted_tos = form.cleaned_data['accepted_tos']
            db_api_key.save()
            form = ApiV2ClientForm()
    else:
        if settings.APIV2KEYS_ALLOWED_FOR_APIV1:
            user_credentials = list(request.user.apiv2_client.all()) + list(request.user.api_keys.all())
        else:
            user_credentials = request.user.apiv2_client.all()
        form = ApiV2ClientForm()
    return render_to_response('api/apply_key_apiv2.html',
                              { 'user': request.user,
                                'form': form,
                                'user_credentials': user_credentials,
                                'combined_apiv1_and_apiv2': settings.APIV2KEYS_ALLOWED_FOR_APIV1
                              }, context_instance=RequestContext(request))