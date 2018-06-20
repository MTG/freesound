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

from __future__ import absolute_import
from sounds.models import Sound
from django import template
from django.conf import settings

register = template.Library()


@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound(context, sound):
    """
    When a sound object is passed make sure to call select_related for license and user so it's already fetched
    """

    if isinstance(sound, Sound):
        sound_id = sound.id
        sound_obj = sound
    else:
        sound_id = int(sound)
        try:
            sound_obj = Sound.objects.select_related('license', 'user').get(id=sound_id)
        except Sound.DoesNotExist:
            sound_obj = None

    is_explicit = False
    if sound_obj is not None:
        request = context['request']
        is_explicit = sound_obj.is_explicit and \
                (not request.user.is_authenticated or \
                        not request.user.profile.is_adult)
    return {
        'sound_id':     sound_id,
        'sound':        sound_obj,
        'sound_tags':   sound_obj.get_sound_tags(12),
        'sound_user':   sound_obj.user.username,
        'license_name': sound_obj.license.name,
        'media_url':    context['media_url'],
        'request':      context['request'],
        'is_explicit':  is_explicit,
        'is_authenticated': request.user.is_authenticated(),
    }


@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_raw_sound(context, sound):
    sound_id = sound.id
    request = context['request']
    is_explicit = sound.is_explicit and (not request.user.is_authenticated \
            or not request.user.profile.is_adult)

    return {
        'sound_id':     sound_id,
        'sound':        sound,
        'sound_tags':   sound.tag_array,
        'sound_user':   sound.username,
        'license_name': sound.license_name,
        'media_url':    context['media_url'],
        'request':      request,
        'is_explicit':  is_explicit,
        'is_authenticated': request.user.is_authenticated(),
    }
