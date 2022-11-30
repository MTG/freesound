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

import math

from django import template
from django.conf import settings
from django.urls import reverse

from follow.follow_utils import is_user_following_tag
from general.templatetags.paginator import show_paginator
from general.templatetags.plausible import plausible_scripts
from ratings.models import SoundRating

register = template.Library()


@register.inclusion_tag('atoms/icon.html')
def bw_icon(name, class_name=''):
    """
    Displays a Beast Whoosh icon with the given name
    """
    return {'name': name, 'class_name': class_name}


@register.inclusion_tag('atoms/tag.html')
def bw_tag(tag_name, size=1, class_name="", url=None, weight=None):
    """
    Displays a Beast Whoosh tag with the given name
    """
    if url is None:
        url = reverse('tags', args=[tag_name])
    if weight is None:
        opacity_class = 'opacity-050'
    else:
        opacity_class = 'opacity-' + str(int(math.ceil(pow(weight, 0.6) * 10) * 10)).zfill(3)

    line_height_class = 'line-height-fs-3' if size < 4 else 'line-height-fs-1'

    return {'tag_name': tag_name,
            'size': size,
            'class_name': class_name,
            'line_height_class': line_height_class,
            'url': url,
            'opacity_class': opacity_class}


@register.inclusion_tag('atoms/avatar.html')
def bw_user_avatar(avatar_url, username, size=40, extra_class=''):
    """
    Displays a Beast Whoosh user avatar or no avatar if user has none
    We check if user has custom avatar by checking if the given avatar URL contains the filename of the default
    avatar for Freesound 2 UI. Once we get rid of old UI code, this function can be modified as the locations
    decorator of the Profile model might return something different if user has no avatar.
    """
    if len(username) > 1:
        no_avatar_bg_color = settings.AVATAR_BG_COLORS[(ord(username[0]) + ord(username[1])) % len(settings.AVATAR_BG_COLORS)]
    else:
        no_avatar_bg_color = settings.AVATAR_BG_COLORS[ord(username[0]) % len(settings.AVATAR_BG_COLORS)]

    return {
        'size': size,
        'has_avatar': '_avatar.png' not in avatar_url,
        'avatar_url':avatar_url,
        'username': username,
        'font_size': int(size * 0.4),
        'extra_class': extra_class,
        'no_avatar_bg_color': no_avatar_bg_color}


@register.inclusion_tag('atoms/stars.html', takes_context=True)
def bw_sound_stars(context, sound, allow_rating=None, use_request_user_rating=False, update_stars_color_on_save=False):
    if hasattr(sound, 'username'):
        sound_user = sound.username
    else:
        sound_user = sound.user.username
    request = context['request']
    request_user = request.user.username
    is_authenticated = request.user.is_authenticated

    if allow_rating is None:
        # If allow_rating is None (default), allow rating only if the request user is not the author of the sound
        allow_rating = request.user.id != sound.user_id

    if not use_request_user_rating:
        if sound.num_ratings >= settings.MIN_NUMBER_RATINGS:
            sound_rating = sound.avg_rating
        else:
            sound_rating = 0
    else:
        try:
            sound_rating = sound.ratings.get(user=request.user).rating
        except (SoundRating.DoesNotExist, TypeError):
            sound_rating = 0

    # Pre process rating values to do less work in the template
    stars_10 = []
    for i in range(0, 10):
        if sound_rating >= i + 1:
            stars_10.append(True)
        else:
            stars_10.append(False)
    stars_5 = []
    for i in range(0, 10, 2):
        if stars_10[i] and stars_10[i + 1]:
            stars_5.append('full')
        elif not stars_10[i] and not stars_10[i + 1]:
            stars_5.append('empty')
        else:
            stars_5.append('half')

    return {'sound_user': sound_user,
            'allow_rating': is_authenticated and allow_rating,
            'sound': sound,
            'update_stars_color_on_save': update_stars_color_on_save,
            'stars_range': zip(stars_5, list(range(1, 6)))}


@register.inclusion_tag('atoms/stars.html', takes_context=True)
def bw_generic_stars(context, rating_0_10):
    # Expects rating in 0-10 scale
    stars_10 = []
    for i in range(0, 10):
        if rating_0_10 >= i + 1:
            stars_10.append(True)
        else:
            stars_10.append(False)
    stars_5 = []
    for i in range(0, 10, 2):
        if stars_10[i] and stars_10[i + 1]:
            stars_5.append('full')
        elif not stars_10[i] and not stars_10[i + 1]:
            stars_5.append('empty')
        else:
            stars_5.append('half')

    return {
        'allow_rating': False,
        'update_stars_color_on_save': False,
        'stars_range': zip(stars_5, list(range(1, 6)))
    }


@register.inclusion_tag('molecules/paginator.html', takes_context=True)
def bw_paginator(context, paginator, page, current_page, request, anchor="", non_grouped_number_of_results=-1):
    return show_paginator(context, paginator, page, current_page, request,
                          anchor=anchor, non_grouped_number_of_results=non_grouped_number_of_results)


@register.inclusion_tag('molecules/maps_js_scripts.html', takes_context=True)
def bw_maps_js_scripts(context):
    return {'mapbox_access_token': settings.MAPBOX_ACCESS_TOKEN,
            'media_url': settings.MEDIA_URL}


@register.filter
def user_following_tags(user, tags_slash):
    if user.is_authenticated():
        return is_user_following_tag(user, tags_slash)
    else:
        return False


@register.inclusion_tag('molecules/plausible_scripts.html', takes_context=False)
def bw_plausible_scripts():
    return plausible_scripts()
