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
from django.shortcuts import get_object_or_404

from fscollections.models import Collection
from sounds.models import Sound

register = template.Library()


@register.inclusion_tag("collections/display_collection.html", takes_context=True)
def display_collection(context, collection_id):
    collection = get_object_or_404(Collection, id=collection_id)
    request = context.get("request")
    if collection.featured_sound_ids:
        header_sounds = Sound.public.filter(id__in=collection.featured_sound_ids)
    else:
        header_sounds = Sound.public.filter(collections=collection)[:1]
    
    tvars = {"collection": collection, "header_sounds": header_sounds, "request": request}
    return tvars

