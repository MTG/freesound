# Create your views here.
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.paginator import Paginator, InvalidPage
from django.db.models import Count, Max
from django.http import HttpResponseRedirect

from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.db.models import Q
from sounds.models import Sound

def tags(request, multiple_tags=None):
    if multiple_tags:
        multiple_tags = multiple_tags.split('/')
    else:
        multiple_tags = []
    
    multiple_tags = sorted(filter(lambda x:x, multiple_tags))
    
    sounds = Sound.objects.filter(processing_state="OK", moderation_state="OK")
    for tag in multiple_tags:
        sounds = sounds.filter(tags__tag__name=tag)

    paginator = Paginator(sounds, settings.SOUNDS_PER_PAGE)

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        current_page = 1

    try:
        page = paginator.page(current_page)
    except InvalidPage:
        page = paginator.page(1)
        current_page = 1

    return render_to_response('sounds/tags.html', locals(), context_instance=RequestContext(request))