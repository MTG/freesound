from django.template import Library
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse

register = Library()

@register.filter
def rating_url(object, rating):
    content_type = ContentType.objects.get_for_model(object.__class__)
    return reverse("ratings-rate", kwargs=dict(content_type_id=content_type.id, object_id=object.id, rating=rating))