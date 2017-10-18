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

from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from ratings.models import Rating
from sounds.models import Sound
from utils.cache import invalidate_template_cache
from django.db import transaction

@login_required
@transaction.atomic()
def add(request, content_type_id, object_id, rating):
    rating = int(rating)
    content_type = ContentType.objects.get(id=content_type_id)
    if rating in range(1,6):
        # in order to keep the ratings compatible with freesound 1, we multiply by two...
        rating = rating*2
        rating_obj, created = Rating.objects.get_or_create(
                user=request.user,
                object_id=object_id,
                content_type=content_type, defaults={'rating': rating})

        if not created:
            rating_obj.rating = rating
            rating_obj.save()

        # make sure the rating is seen on the next page load by invalidating the cache for it.
        ct = ContentType.objects.get(id=content_type_id)
        if ct.name == 'sound':
            invalidate_template_cache("sound_header", object_id, True)
            invalidate_template_cache("sound_header", object_id, False)
            invalidate_template_cache("display_sound", object_id, True, 'OK')
            invalidate_template_cache("display_sound", object_id, False, 'OK')
            Sound.objects.filter(id=object_id).update(is_index_dirty=True)  # Set index dirty to true

    return HttpResponse(str(Rating.objects.filter(object_id=object_id, content_type=content_type).count()))
