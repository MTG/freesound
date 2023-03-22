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


from django import template
from django.conf import settings

from sounds.models import Sound
from sounds.templatetags.display_sound import display_sound_small_no_bookmark

register = template.Library()


@register.inclusion_tag('molecules/sounds_selector.html', takes_context=True)
def sounds_selector(context, sounds, selected_sound_ids=[], show_select_all_buttons=False):
    if sounds:
        if not isinstance(sounds[0], Sound):
            # sounds are passed as a list of sound ids, retrieve the Sound objects from DB
            sounds = Sound.objects.ordered_ids(sounds)
        for sound in sounds:
            sound.selected = sound.id in selected_sound_ids
    return {
        'sounds': sounds,
        'show_select_all_buttons': show_select_all_buttons,
        'original_context': context  # This will be used so a nested inclusion tag can get the original context
    }

@register.inclusion_tag('molecules/sounds_selector.html', takes_context=True)
def sounds_selector_with_select_buttons(context, sounds, selected_sound_ids=[]):
    return sounds_selector(context, sounds, selected_sound_ids=selected_sound_ids, show_select_all_buttons=True)
