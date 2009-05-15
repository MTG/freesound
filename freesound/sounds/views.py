from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.paginator import Paginator, InvalidPage
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from forum.models import Post
from sounds.models import Sound
from comments.models import Comment

def front_page(request):
    rss_url = settings.FREESOUND_RSS
    pledgie_campaign = 4045

    latest_forum_posts = Post.objects.select_related('author', 'thread', 'thread__forum').all().order_by("-created")[0:10]
    latest_additions = Sound.objects.latest_additions(5)
    
    cache_key = "random_sound"
    random_sound = cache.get(cache_key)
    if not random_sound:
        random_sound = Sound.objects.random()
        cache.set(cache_key, random_sound, 60*60*24)
    
    return render_to_response('index.html', locals(), context_instance=RequestContext(request)) 
 
def sounds(request):
    pass

def sound(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")

    content_type = ContentType.objects.get_for_model(Sound)

    paginator = Paginator(Comment.objects.filter(content_type=content_type, object_id=sound_id), settings.SOUND_COMMENTS_PER_PAGE)

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        current_page = 1

    try:
        page = paginator.page(current_page)
    except InvalidPage:
        page = paginator.page(1)
        current_page = 1

    return render_to_response('sounds/sound.html', locals(), context_instance=RequestContext(request))

def remixes(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")
    pass

def sources(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")
    pass

def geotag(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")
    google_api_key = settings.GOOGLE_API_KEY
    return render_to_response('sounds/geotag.html', locals(), context_instance=RequestContext(request))

def similar(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")
    pass

def pack(request, pack_id):
    pass

def remixed(request):
     pass
 
def random(request):
     pass

def packs(request):
    pass

def packs_for_user(request, username):
    pass

def search(request):
    pass

def for_user(request, username):
    pass

