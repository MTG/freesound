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

from fscollections.models import Collection, CollectionSound
from sounds.models import Sound
from django.shortcuts import get_object_or_404

register = template.Library()


@register.inclusion_tag("collections/display_collection.html", takes_context=True)
def display_collection(context, collection_id):
    collection = get_object_or_404(Collection, id=collection_id)
    request = context.get("request")
    try:
        sound = Sound.objects.get(collections=collection, collectionsound__featured_sound=True)
    except Sound.DoesNotExist:
        sound = None
    tvars = {"collection": collection, "ft_sound": sound, "request": request}
    return tvars
