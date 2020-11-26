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
from django.urls import reverse

from general.templatetags.paginator import show_paginator

register = template.Library()


@register.inclusion_tag('atoms/icon.html')
def bw_icon(name, class_name=''):
    """
    Displays a Beast Whoosh icon with the given name
    """
    return {'name': name, 'class_name': class_name}


@register.inclusion_tag('atoms/tag.html')
def bw_tag(tag_name, size=1, class_name=""):
    """
    Displays a Beast Whoosh tag with the given name
    """
    url = reverse('tags', args=[tag_name])
    return {'tag_name': tag_name, 'size': size, 'class_name': class_name, 'url': url}

@register.inclusion_tag('atoms/stars.html', takes_context=True)
def bw_sound_stars(context):
    sound = context['sound']
    if hasattr(sound, 'username'):
        sound_user = sound.username
    else:
        sound_user = sound.user.username
    request = context['request']
    request_user = request.user.username
    is_authenticated = request.user.is_authenticated

    if sound.num_ratings >= settings.MIN_NUMBER_RATINGS:
        sound_avg_rating = sound.avg_rating
    else:
        sound_avg_rating = 0

    # Pre process rating values to do less work in the template
    stars_10 = []
    for i in range(0, 10):
        if sound_avg_rating >= i + 1:
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
            'request_user': request_user,
            'is_authenticated': is_authenticated,
            'sound': sound,
            'stars_5': stars_5}


@register.inclusion_tag('molecules/paginator.html', takes_context=True)
def bw_paginator(context, paginator, page, current_page, request, anchor="", non_grouped_number_of_results=-1):
    return show_paginator(context, paginator, page, current_page, request,
                          anchor=anchor, non_grouped_number_of_results=non_grouped_number_of_results )
