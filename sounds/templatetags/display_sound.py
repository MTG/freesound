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
#avoid namespace clash with 'tags' templatetag
from tags.models import TaggedItem as ti
from django.contrib.contenttypes.models import ContentType
from sounds.models import Sound
from django import template
import settings

register = template.Library()
sound_content_type = ContentType.objects.get_for_model(Sound)

@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound(context, sound):

    if isinstance(sound, Sound):
        sound_id = sound.id
        sound_obj = [sound]
    else:
        sound_id = int(sound)
        try:
            #sound_obj = Sound.objects.get(id=sound_id)
            sound_obj = Sound.objects.select_related().filter(id=sound) # need to use filter here because we don't want the query to be evaluated already!
        except Sound.DoesNotExist:
            sound_obj = []

    return { 'sound_id':     sound_id,
             'sound':        sound_obj,
             'sound_tags':   ti.objects.select_related() \
                                .filter(object_id=sound_id, content_type=sound_content_type)[0:12],
             'do_log':       settings.LOG_CLICKTHROUGH_DATA,
             'media_url':    context['media_url'],
             'request':      context['request']
           }
