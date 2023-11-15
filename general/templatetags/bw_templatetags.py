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
import urllib.request, urllib.parse, urllib.error

from django import template
from django.conf import settings
from django.contrib.humanize.templatetags.humanize import intcomma
from django.urls import reverse

from follow.follow_utils import is_user_following_tag
from general.templatetags.plausible import plausible_scripts
from ratings.models import SoundRating

register = template.Library()


@register.inclusion_tag('atoms/icon.html')
def bw_icon(name, class_name=''):
    """
    Displays a BW icon with the given name
    """
    return {'name': name, 'class_name': class_name}


@register.inclusion_tag('atoms/tag.html')
def bw_tag(tag_name, size=1, class_name="", url=None, weight=None):
    """
    Displays a BW tag with the given name
    """
    if url is None:
        url = reverse('tags', args=[tag_name])
    if weight is None:
        opacity_class = 'opacity-050'
    else:
        opacity_class = 'opacity-' + str(int(math.ceil(pow(weight, 0.6) * 10) * 10)).zfill(3)

    line_height_class = 'line-height-38' if size < 4 else 'line-height-fs-1'

    return {'tag_name': tag_name,
            'size': size,
            'class_name': class_name,
            'line_height_class': line_height_class,
            'url': url,
            'opacity_class': opacity_class}


@register.inclusion_tag('atoms/avatar.html')
def bw_user_avatar(avatar_url, username, size=40, extra_class=''):
    """
    Displays a BW user avatar or no avatar if user has none
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
        'avatar_url':avatar_url,
        'username': username,
        'font_size': int(size * 0.4),
        'extra_class': extra_class,
        'no_avatar_bg_color': no_avatar_bg_color}


@register.inclusion_tag('atoms/stars.html', takes_context=True)
def bw_sound_stars(context, sound, allow_rating=True, use_request_user_rating=False, show_added_rating_on_save=False):
    if isinstance(sound, dict):
        sound_user = sound['username']
        sound_avg_rating = sound['avg_rating']
        sound_num_ratings = sound['num_ratings']
    else:
        if hasattr(sound, 'username'):
            sound_user = sound.username
        else:
            sound_user = sound.user.username
        sound_avg_rating = sound.avg_rating
        sound_num_ratings = sound.num_ratings
    request = context['request']

    user_has_rated_this_sound = False
    if not use_request_user_rating:
        if sound_num_ratings >= settings.MIN_NUMBER_RATINGS:
            sound_rating = sound_avg_rating
        else:
            sound_rating = 0
    else:
        try:
            sound_rating = sound.ratings.get(user=request.user).rating
            user_has_rated_this_sound = True
        except (SoundRating.DoesNotExist, TypeError):
            sound_rating = 0
    has_min_ratings = sound_num_ratings >= settings.MIN_NUMBER_RATINGS

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
            'allow_rating': allow_rating,
            'sound': sound,
            'sound_rating_0_5': sound_rating/2,
            'user_has_rated_this_sound': user_has_rated_this_sound,
            'has_min_ratings': has_min_ratings,
            'show_added_rating_on_save': show_added_rating_on_save,
            'use_request_user_rating': use_request_user_rating,
            'fill_class': 'text-red' if not use_request_user_rating else 'text-yellow',
            'stars_range': list(zip(stars_5, list(range(1, 6))))}


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

    has_min_ratings = rating_0_10 > 0

    return {
        'allow_rating': False,
        'show_added_rating_on_save': False,
        'fill_class': 'text-red',
        'has_min_ratings': has_min_ratings,
        'stars_range': list(zip(stars_5, list(range(1, 6))))
    }


@register.inclusion_tag('molecules/paginator.html', takes_context=True)
def bw_paginator(context, paginator, page, current_page, request, anchor="", non_grouped_number_of_results=-1):
    """
    Adds pagination context variables for use in displaying first, adjacent and
    last page links in addition to those created by the object_list generic
    view.
    """
    if paginator is None:
        # If paginator object is None, don't go ahead as below calculations will fail. This can happen if show_paginator
        # is called and no paginator object is present in view
        return {}
 
    adjacent_pages = 3
    total_wanted = adjacent_pages * 2 + 1
    min_page_num = max(current_page - adjacent_pages, 1)
    max_page_num = min(current_page + adjacent_pages + 1, paginator.num_pages + 1)

    num_items = max_page_num - min_page_num

    if num_items < total_wanted and num_items < paginator.num_pages:
        if min_page_num == 1:
            # we're at the start, increment max_page_num
            max_page_num += min(total_wanted - num_items, paginator.num_pages - num_items)
        else:
            # we're at the end, decrement
            min_page_num -= min(total_wanted - num_items, paginator.num_pages - num_items)

    # although paginator objects are 0-based, we use 1-based paging
    page_numbers = [n for n in range(min_page_num, max_page_num) if 0 < n <= paginator.num_pages]
    params = urllib.parse.urlencode([(key.encode('utf-8'), value.encode('utf-8')) for (key, value) in request.GET.items()
                               if key.lower() != "page"])

    if params == "":
        url = request.path + "?page="
    else:
        url = request.path + "?" + params + "&page="

    # The pagination could be over a queryset or over the result of a query to solr, so 'page' could be an object
    # if it's the case a query to the DB or a dict if it's the case of a query to solr
    if isinstance(page, dict):
        url_prev_page = url + str(page['previous_page_number'])
        url_next_page =  url + str(page['next_page_number'])
        url_first_page = url + '1'
    else:
        url_prev_page = None
        if page.has_previous():
             url_prev_page = url + str(page.previous_page_number())
        url_next_page = None
        if page.has_next():
             url_next_page = url + str(page.next_page_number())
        url_first_page = url + '1'
    url_last_page = url + str(paginator.num_pages)

    if page_numbers:
        last_is_next = paginator.num_pages - 1 == page_numbers[-1]
    else:
        last_is_next = False

    return {
        "page": page,
        "paginator": paginator,
        "current_page": current_page,
        "page_numbers": page_numbers,
        "show_first": 1 not in page_numbers,
        "show_last": paginator.num_pages not in page_numbers,
        "last_is_next": last_is_next,
        "url" : url,
        "url_prev_page": url_prev_page,
        "url_next_page": url_next_page,
        "url_first_page": url_first_page,
        "url_last_page": url_last_page,
        "anchor": anchor,
        "non_grouped_number_of_results": non_grouped_number_of_results
    }


@register.inclusion_tag('molecules/maps_js_scripts.html', takes_context=True)
def bw_maps_js_scripts(context):
    return {'mapbox_access_token': settings.MAPBOX_ACCESS_TOKEN}


@register.filter
def user_following_tags(user, tags_slash):
    if user.is_authenticated:
        return is_user_following_tag(user, tags_slash)
    else:
        return False


@register.inclusion_tag('molecules/plausible_scripts.html', takes_context=False)
def bw_plausible_scripts():
    return plausible_scripts()


@register.filter
def bw_intcomma(value):
    return intcomma(value)


@register.inclusion_tag('molecules/carousel.html', takes_context=True)
def sound_carousel(context, sounds, show_timesince=False):
    # Update context and pass it to templatetag so nested template tags also have it
    context.update({'elements': sounds, 'type': 'sound', 'show_timesince': show_timesince})  
    return context


@register.inclusion_tag('molecules/carousel.html', takes_context=True)
def sound_carousel_with_timesince(context, sounds):
    return sound_carousel(context, sounds, show_timesince=True)


@register.inclusion_tag('molecules/carousel.html', takes_context=True)
def pack_carousel(context, packs):
    # Update context and pass it to templatetag so nested template tags also have it
    context.update({'elements': packs, 'type': 'pack'})
    return context