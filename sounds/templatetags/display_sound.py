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
from random import randint

from accounts.models import Profile
from sounds.models import Sound

register = template.Library()


@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound(context, sound, player_size='small', show_bookmark=None, show_similar_sounds=None, show_remix=None, show_rate_widget=False, show_timesince=False):
    """This templatetag is used to display a sound with its player. It prepares some variables that are then passed
    to the display_sound.html template to show sound information together with the player.

    Args:
        context (django.template.Context): an object with contextual information for rendering a template. This
          argument is automatically added by Django when calling the templatetag inside a template.
        sound (int or Sound): sound ID or Sound object of the sound that will be shown. If no sound exists for the
          given ID, the display_sound.html will be rendered with empty HTML.
        player_size (str, optional): size of the player to display. See functions below and template file for 
          available sizes. Information about the contents of each size is given in the display_sound.html template code.
        show_bookmark (bool, optional): whether or not to show the bookmark button (BW frontend only). If set to None
          it will be decided based on player size and other properties.
        show_similar_sounds (bool, optional): whether or not to show the similar sounds button (BW frontend only). If set to None
          it will be decided based on player size and other properties.
        show_remix (bool, optional): whether or not to show the sound's remix group button (BW frontend only). If set to None
          it will be decided based on player size and other properties.
        show_rate_widget (bool, optional): whether or not to show the widget for ratings sounds (BW frontend only). Note that rate
          widget can only be shown in small players.
        show_timesince (bool, optional): whether an indicator of the time since the sound was created (i.e. "3 years ago") instead
          of the absolute date (i.e. "November 3rd, 2023") should be used. This only applies to the "small" player size and uses
          javascript to replace the default date with the timesince indicator.

    Returns:
        dict: dictionary with the variables needed for rendering the sound with the display_sound.html template

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
            # Note that we don't re-retrieve when player size contains "no_info" as in these cases there is
            # no extra metadata needed to be shown.
            if 'no_info' not in player_size:
                sound_obj = get_sound_using_bulk_query_id(sound.id)
            else:
                sound_obj = sound
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
            'sound': sound_obj,
            'user_profile_locations': Profile.locations_static(sound_obj.user_id, getattr(sound_obj, 'user_has_avatar', False)),
            'request': request,
            'is_explicit': sound_obj.is_explicit and
                           (not request.user.is_authenticated or not request.user.profile.is_adult),
            'is_authenticated': request.user.is_authenticated,
            'show_bookmark_button': show_bookmark if show_bookmark is not None else (player_size == 'small' or player_size == 'small_no_info' or player_size == 'big_no_info'),  # Only BW
            'show_similar_sounds_button': show_similar_sounds if show_similar_sounds is not None else (player_size == 'small' or player_size == 'small_no_info' or player_size == 'big_no_info'),  # Only BW
            'show_remix_group_button': show_remix if show_remix is not None else (player_size == 'small' or player_size == 'small_no_info' or player_size == 'big_no_info'),  # Only BW
            'show_rate_widget': show_rate_widget if (player_size == 'small' or player_size == 'small_no_info') else False,  # Only BW
            'request_user_is_author': request.user.is_authenticated and sound_obj.user_id == request.user.id,
            'player_size': player_size,
            'show_milliseconds': 'true' if (player_size == 'big_no_info' or sound_obj.duration < 10) else 'false',  # Only BW
            'show_timesince': show_timesince,
            'min_num_ratings': settings.MIN_NUMBER_RATINGS,
            'random_number': randint(1, 1000000),  # Used to generate IDs for HTML elements that need to be unique per sound/player instance
        }


@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound_small(context, sound):
    return display_sound(context, sound, player_size='small', show_rate_widget=True)

@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound_small_with_timesince(context, sound):
    return display_sound(context, sound, player_size='small', show_rate_widget=True, show_timesince=True)

@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound_moderation(context, sound):
    return display_sound(context, sound, player_size='moderation', show_bookmark=False, show_similar_sounds=False, show_remix=True, show_rate_widget=False)

@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound_small_no_bookmark(context, sound):
    return display_sound(context, sound, player_size='small', show_bookmark=False, show_similar_sounds=False, show_remix=False, show_rate_widget=True)

@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound_small_no_bookmark_no_ratings(context, sound):
    return display_sound(context, sound, player_size='small', show_bookmark=False, show_similar_sounds=False, show_remix=False, show_rate_widget=False)

@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound_middle(context, sound):
    return display_sound(context, sound, player_size='middle', show_bookmark=True, show_similar_sounds=True, show_remix=True)

@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound_big_no_info(context, sound):
    return display_sound(context, sound, player_size='big_no_info')

@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound_big_no_info_no_bookmark(context, sound):
    return display_sound(context, sound, player_size='big_no_info', show_bookmark=False, show_similar_sounds=False, show_remix=False)

@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound_small_no_info(context, sound):
    return display_sound(context, sound, player_size='small_no_info', show_rate_widget=True)

@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound_small_no_info_no_buttons(context, sound):
    return display_sound(context, sound, player_size='small_no_info', show_rate_widget=False, show_bookmark=False, show_similar_sounds=False, show_remix=False)

@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound_minimal(context, sound):
    return display_sound(context, sound, player_size='minimal')

@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound_no_sound_object(context, file_data, player_size, show_bookmark=True, show_similar_sounds=True, show_remix=True):
    '''
    This player works for sounds which have no Sound object. It requires
    URLs to the sound files (mp3 and ogg)a and the wave/spectral images, and
    the duration of the sound the JS player can be created. This data is 
    passed through the file_data argument. Here is an example of how file_data 
    should look like if preapring it from a Sound object:
    
    file_data = {
        'duration': sound.duration,
        'samplerate': sound.samplerate,  # Useful for the ruler of the player, if not indicated, a default will be assumed
        'preview_mp3': sound.locations('preview.LQ.mp3.url'),
        'preview_ogg': sound.locations('preview.LQ.ogg.url'),
        'wave': sound.locations('display.wave_bw.L.url'),
        'spectral': sound.locations('display.spectral_bw.L.url'),
        'id': sound.id,  # Only used for sounds that do actually have a sound object so we can display bookmark/similarity buttons
        'username': sound.user.username,  # Only used for sounds that do actually have a sound object so we can display bookmark/similarity/remix buttons
        'similarity_state': sound.similarity_state  # Only used for sounds that do actually have a sound object so we can display bookmark/similarity/remix buttons
        'remixgroup_id': sound.remixgroup_id  # Only used for sounds that do actually have a sound object so we can display bookmark/similarity/remix buttons
        'num_ratings': sound.num_ratings,  # Used to display rating widget in players
        'avg_rating': sound.avg_rating,  # Used to display rating widget in players
    }
    '''
    return {
        'sound': {
            'id': file_data.get('id', file_data['preview_mp3'].split('/')[-2]),  # If no id, use a unique fake ID to avoid caching problems
            'username': file_data.get('username', 'nousername'),
            'similarity_state': file_data.get('similarity_state', 'FA'),
            'duration': file_data['duration'],
            'samplerate': file_data.get('samplerate', 44100),
            'num_ratings': file_data.get('num_ratings', 0),
            'avg_rating': file_data.get('avg_rating', 0.0),
            'locations': {
                'preview': {
                    'LQ': {
                        'mp3': {'url': file_data['preview_mp3']},
                        'ogg': {'url': file_data['preview_ogg']}
                    }
                },
                'display': {
                    'wave_bw': {
                        'M': {'url': file_data['wave']},
                        'L': {'url': file_data['wave']}
                    }, 
                    'spectral_bw': {
                        'M': {'url': file_data['spectral']},
                        'L': {'url': file_data['spectral']}
                    }
                }
            }
        },
        'show_milliseconds': 'true' if ('big' in player_size ) else 'false',
        'show_bookmark_button': show_bookmark and 'id' in file_data,
        'show_similar_sounds_button': show_similar_sounds and 'similarity_state' in file_data,
        'show_remix_group_button': show_remix and 'remixgroup_id' in file_data,
        'show_rate_widget': 'avg_rating' in file_data,
        'player_size': player_size,
        'request': context['request']
    }

@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound_big_no_sound_object(context, file_data):
    return display_sound_no_sound_object(context, file_data, player_size='big_no_info')


@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound_small_no_sound_object(context, file_data):
    return display_sound_no_sound_object(context, file_data, player_size='small_no_info')
   
@register.inclusion_tag('sounds/display_sound.html', takes_context=True)
def display_sound_small_no_sound_object_no_bookmark(context, file_data):
    return display_sound_no_sound_object(context, file_data, player_size='small_no_info', show_bookmark=False, show_similar_sounds=False, show_remix=False)

@register.inclusion_tag('sounds/display_sound_selectable.html', takes_context=True)
def display_sound_small_selectable(context, sound, selected=False):
    context = context.get('original_context', context)  # This is to allow passing context in nested inclusion tags
    tvars = display_sound_small_no_bookmark_no_ratings(context, sound)
    tvars.update({
        'selected': selected,
    })
    return tvars
