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
from apiv2.authentication import OAuth2Authentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated


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
    permission_classes = (IsAuthenticated,)
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
    serializer_class = SoundListSerializer

    def get_queryset(self):
        return Sound.objects.select_related('user').filter(moderation_state="OK",
                                                           processing_state="OK",
                                                           user__id=self.kwargs['pk'])

