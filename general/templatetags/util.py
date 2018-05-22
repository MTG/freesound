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

from django.template import Library
import datetime, time
from django.template.defaultfilters import stringfilter
from django.forms import CheckboxInput

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
    duration_minutes = int(value/60)
    duration_seconds = int(value) % 60
    duration_miliseconds = int((value - int(value)) * 1000)
    return "%02d:%02d:%03d" % (duration_minutes, duration_seconds, duration_miliseconds)

@register.filter
def in_list(value,arg):
    return value in arg
