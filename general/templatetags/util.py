from __future__ import division
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

from builtins import range
from past.utils import old_div
import datetime
import time

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
        return value[:length-3] + u"..."
    else:
        return value


@register.filter
def duration(value):
    duration_minutes = int(old_div(value,60))
    duration_seconds = int(value) % 60
    duration_miliseconds = int((value - int(value)) * 1000)
    return "%d:%02d.%03d" % (duration_minutes, duration_seconds, duration_miliseconds)


@register.filter
def duration_hours(total_seconds):
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    return '{}:{:02d}'.format(hours, minutes)


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
    if type(l) is not list:
        l = list(l)
    return [l[i:i + n] for i in range(0, len(l), n)]


@register.filter
def license_with_version(license_name, license_deed_url):
    if '3.0' in license_deed_url:
        return '{} 3.0'.format(license_name)
    elif '4.0' in license_deed_url:
        return '{} 4.0'.format(license_name)
    return license_name


@register.filter
def element_at_index(l, index):
    return l[index]
