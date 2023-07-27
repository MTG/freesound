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

import datetime
import time

from django.utils.safestring import mark_safe
from django.template import Library
from django.template.defaultfilters import stringfilter

register = Library()


@register.filter
def tuple_to_time(t):
    return datetime.datetime(*t[0:6]) + datetime.timedelta(seconds=time.timezone)


@register.filter(name='truncate_string')
@stringfilter
def truncate_string(value, length):
    if len(value) > length:
        return value[:length-3] + "..."
    else:
        return value


@register.filter
def duration(value):
    duration_minutes = int(value / 60)
    duration_seconds = int(value) % 60
    duration_miliseconds = int((value - int(value)) * 1000)
    return "%d:%02d.%03d" % (duration_minutes, duration_seconds, duration_miliseconds)


@register.filter
def duration_hours(total_seconds):
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    return f'{hours}:{minutes:02d}'


@register.filter
def formatnumber(number):
    if 1000 <= number < 1000000:
        return f'{number/1000:.1f}K'
    elif 1000000 <= number:
        return f'{number/1000000:.1f}M'
    else:
        return f'{number}'


@register.filter
def in_list(value,arg):
    return value in arg


@register.filter
def chunks(l, n):
    """
    Returns the elements of l grouped in chunks of size n.
    :param list l: list of elements to regroup
    :param int n: number of elements per group
    :return: list of n-sized lists
    """
    if not isinstance(l, list):
        l = list(l)
    return [l[i:i + n] for i in range(0, len(l), n)]


@register.filter
def license_with_version(license_name, license_deed_url):
    if '3.0' in license_deed_url:
        return f'{license_name} 3.0'
    elif '4.0' in license_deed_url:
        return f'{license_name} 4.0'
    return license_name


@register.filter
def element_at_index(l, index):
    return l[index]


@register.filter
def strip_unnecessary_br(value):
    # In HTMLCleaningFields some HTML tags are allowed. When the contents of these fields are passed to Django's |linebreaks
    # templatetag, <br> tags can be inserted between other HTML tags (linebreaks is not HTML-aware). This templatetag
    # implements a hacky fix for the most common issue which is the unnecessary br elements introduced after ul and li elements.
    value = value.replace('</li><br>', '</li>')
    value = value.replace('<ul><br>', '<ul>')
    value = value.replace('</ul><br>', '</ul>')
    return mark_safe(value)
