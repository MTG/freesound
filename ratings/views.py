from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from ratings.models import Rating
from utils.cache import invalidate_template_cache

@login_required
def add(request, content_type_id, object_id, rating):
    rating = int(rating)
    if rating in range(1,6):
        # in order to keep the ratings compatible with freesound 1, we multiply by two...
        rating = rating*2
        content_type = ContentType.objects.get(id=content_type_id)
        try:
            rating_object = Rating.objects.get(user=request.user, object_id=object_id, content_type=content_type)
            rating_object.rating = rating;
            rating_object.save()
            # make sure the rating is seen on the next page load by invalidating the cache for it.
            ct = ContentType.objects.get(id=content_type_id)
            if ct.name == 'sound':
                invalidate_template_cache("sound_header", object_id)
                invalidate_template_cache("display_sound", object_id)
            # if you want to invalidate some other caches for other content types add them here
        except Rating.DoesNotExist: #@UndefinedVariable
            rating_object = Rating.objects.create(user=request.user, object_id=object_id, content_type=content_type, rating=rating)
    return HttpResponse(Rating.objects.filter(object_id=object_id, content_type=content_type).count())
