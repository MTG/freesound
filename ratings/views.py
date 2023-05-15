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

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404

from ratings.models import SoundRating
from sounds.models import Sound
from utils.frontend_handling import using_beastwhoosh


@login_required
@transaction.atomic()
def rate_sound(request, username, sound_id, rating):
    sound = get_object_or_404(Sound.objects.select_related("user"), id=sound_id)
    if sound.user.username.lower() != username.lower():
        raise Http404

    rating = int(rating)
    if 1 <= rating <= 5:
        # in order to keep the ratings compatible with freesound 1, we multiply by two...
        rating = rating*2
        rating_obj, created = SoundRating.objects.get_or_create(
                user=request.user,
                sound_id=sound_id, defaults={'rating': rating})

        if not created:
            rating_obj.rating = rating
            rating_obj.save()

        # make sure the rating is seen on the next page load by invalidating the cache for it.
        sound.invalidate_template_caches()
        Sound.objects.filter(id=sound_id).update(is_index_dirty=True)  # Set index dirty to true
        
    if using_beastwhoosh(request):
        sound.refresh_from_db()
        return JsonResponse({
            'num_ratings': sound.num_ratings, 
            'num_ratings_display': sound.get_ratings_count_text(),
            'num_ratings_display_short': sound.get_ratings_count_text_short(),
            'avg_rating': sound.avg_rating, 
            'min_num_ratings': settings.MIN_NUMBER_RATINGS})
    else:
        return HttpResponse(str(SoundRating.objects.filter(sound_id=sound_id).count()))
