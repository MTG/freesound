from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from ratings.models import Rating

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
        except Rating.DoesNotExist: #@UndefinedVariable
            rating_object = Rating.objects.create(user=request.user, object_id=object_id, content_type=content_type, rating=rating)
    return HttpResponse(Rating.objects.filter(object_id=object_id, content_type=content_type).count()) 