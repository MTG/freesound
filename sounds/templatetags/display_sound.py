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

from django import template

from sounds.models import Sound

register = template.Library()


@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound(context, sound, player_size='small'):
    """This templatetag is used to display a sound with its player. It prepares some variables that are then passed
    to the display_sound.html template to show sound information together with the player. This function is supposed
    to be called from Django templates so it will render the display_sound.html template with the computed variables
    and then add it to the tempalte from which it was called.

    Args:
        context (django.template.Context): an object with contextual information for rendering a template. This
          argument is automatically added by Django when calling the templatetag inside a template.
        sound (int or Sound): sound ID or Sound object of the sound that will be shown. If no sound exists for the
          given ID, the display_sound.html will be rendered with empty HTML.
        player_size (str, optional): size of the player to display. Must be one of ['small', 'big'].
          Defaults to 'small'.

    Returns:
        dict: dictionary with the variables needed for rendering the sound with the display_sound.html templtate

    """

    def get_sound_using_bulk_query_id(sound_id):
        """Get a sound from the DB using the Sound.objects.bulk_query_id method which returns a Sound object with
        some extra properties loaded.

        Args:
            sound_id (int): ID of the sound to retrieve.

        Returns:
            Sound: sound object with extra loaded properties or None if the sound does not exist or the ID is not valid.

        """
        try:
            return Sound.objects.bulk_query_id([int(sound_id)])[0]
        except ValueError:
            # 'sound' is not an integer
            return None
        except IndexError:
            # No sound with given ID exists (Sound.objects.bulk_query_id returns empty qs)
            return None

    def sound_object_retrieved_using_bulk_query_id(sound):
        """Checeks whether the given Sound object has the extra properties that are loaded if the object was
        retrieved usnig the Sound.objects.bulk_query_id method. Sound objects retrieved with bulk_query_id have
        the following extra properties required in the display_sound templatetag: 'tag_array', 'username',
        'license_name'. To optimize the code, we only check for the presence of 'tag_array' and assume the other
        properties will go together.

        Args:
            sound (Sound): Sound object

        Returns:
            bool: True if the object was retrieved using bulk query ID.

        """
        return hasattr(sound, 'tag_array')

    if isinstance(sound, Sound):
        if sound_object_retrieved_using_bulk_query_id(sound):
            sound_obj = sound
        else:
            # If 'sound' is a Sound instance but has not been retrieved using bulk_query_id, we would need to make
            # some extra DB queries to get the metadata that must be rendered. Instead, we retreive again
            # the sound using the bulk_query_id method which will get all needed maetadaata in only one query.
            sound_obj = get_sound_using_bulk_query_id(sound.id)
    else:
        # If 'sound' argument is not a Sound instance then we assume it is a sound ID and we retreive the
        # corresponding object from the DB.
        sound_obj = get_sound_using_bulk_query_id(sound)

    if sound_obj is None:
        return {
            'sound': None,
        }
    else:
        request = context['request']
        return {
            'sound_id':     sound_obj.id,
            'sound':        sound_obj,
            'sound_tags':   sound_obj.tag_array,
            'sound_user':   sound_obj.username,
            'license_name': sound_obj.license_name,
            'media_url':    context['media_url'],
            'request':      request,
            'is_explicit':  sound_obj.is_explicit and
                            (not request.user.is_authenticated or not request.user.profile.is_adult),
            'is_authenticated': request.user.is_authenticated(),
            'player_size': player_size,
        }


@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound_big(context, sound):
    return display_sound(context, sound, player_size='big')
