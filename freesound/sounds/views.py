from comments.models import Comment
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.paginator import Paginator, InvalidPage
from django.db.models import Count, Max
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from forum.models import Post
from sounds.models import Sound, Pack
from utils.forms import HtmlCleaningCharField
from freesound_exceptions import PermissionDenied

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
    try:
        sound = Sound.objects.select_related("license", "user", "pack").get(user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")
    except Sound.DoesNotExist: #@UndefinedVariable
        raise Http404
    
    tags = sound.tags.select_related("tag").all()

    content_type = ContentType.objects.get_for_model(Sound)

    paginator = Paginator(Comment.objects.select_related("user").filter(content_type=content_type, object_id=sound_id), settings.SOUND_COMMENTS_PER_PAGE)

    class CommentForm(forms.Form):
        comment = HtmlCleaningCharField(widget=forms.Textarea)
    
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            sound.comments.add(Comment(content_object=sound, user=request.user, comment=form.cleaned_data["comment"]))
            invalidate_template_cache()
            return HttpResponseRedirect(sound.get_absolute_url())
    else:
        form = CommentForm()

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

def pack(request, username, pack_id):
    pack = get_object_or_404(Pack, user__username__iexact=username, id=pack_id)

    paginator = Paginator(Sound.objects.select_related('user').filter(pack=pack, moderation_state="OK", processing_state="OK"), settings.SOUNDS_PER_PAGE)

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        current_page = 1

    try:
        page = paginator.page(current_page)
    except InvalidPage:
        page = paginator.page(1)
        current_page = 1

    return render_to_response('sounds/pack.html', locals(), context_instance=RequestContext(request))

def remixed(request):
     pass
 
def random(request):
     pass

def packs(request):
    pass

def packs_for_user(request, username):
    user = get_object_or_404(User, username__iexact=username)

    order = request.GET.get("order", "name")
    
    if order not in ["name", "-last_update", "-created", "-num_sounds"]:
        order = "name"
    
    paginator = Paginator(Pack.objects.filter(user=user, sound__moderation_state="OK", sound__processing_state="OK").annotate(num_sounds=Count('sound'), last_update=Max('sound__created')).filter(num_sounds__gt=0).order_by(order), settings.PACKS_PER_PAGE)

    try:
        current_page = int(request.GET.get("page", 1))
    except ValueError:
        current_page = 1

    try:
        page = paginator.page(current_page)
    except InvalidPage:
        page = paginator.page(1)
        current_page = 1

    return render_to_response('sounds/packs.html', locals(), context_instance=RequestContext(request))

def for_user(request, username):
    pass

