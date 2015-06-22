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
from django.contrib.contenttypes.models import ContentType
from sounds.models import Sound
from django import template
from django.conf import settings

register = template.Library()
sound_content_type = ContentType.objects.get_for_model(Sound)

@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound(context, sound):

    if isinstance(sound, Sound):
        sound_id = sound.id
        sound_obj = sound
    else:
        sound_id = int(sound)
        try:
            sound_obj = Sound.objects.get(id=sound_id)
        except Sound.DoesNotExist:
            sound_obj = None

    sound_tags = []
    if sound_obj is not None:
        sound_tags = sound_obj.tags.select_related("tag").all()[0:12]

    return { 'sound_id':     sound_id,
             'sound':        sound_obj,
             'sound_tags':   sound_tags,
             'do_log':       settings.LOG_CLICKTHROUGH_DATA,
             'media_url':    context['media_url'],
             'request':      context['request']
           }

@register.inclusion_tag('sounds/display_raw_sound.html', takes_context=True)
def display_raw_sound(context, sound):
    sound_id = sound.id

    return { 'sound_id':     sound_id,
             'sound':        sound,
             'sound_tags':   sound.tag_array,
             'do_log':       settings.LOG_CLICKTHROUGH_DATA,
             'media_url':    context['media_url'],
             'request':      context['request']
           }
