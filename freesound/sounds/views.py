from comments.forms import CommentForm
from comments.models import Comment
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.servers.basehttp import FileWrapper
from django.core.urlresolvers import reverse
from django.db.models import Count, Max
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from forum.models import Post
from freesound_exceptions import PermissionDenied
from geotags.models import GeoTag
from sounds.forms import SoundDescriptionForm, PackForm, GeotaggingForm, \
    LicenseForm, FlagForm
from accounts.models import Profile
from sounds.models import Sound, Pack, Download
from utils.cache import invalidate_template_cache
from utils.encryption import encrypt, decrypt
from utils.functional import combine_dicts
from utils.mail import send_mail_template
from utils.pagination import paginate
from utils.text import slugify
import os
import datetime

def get_random_sound():
    cache_key = "random_sound"
    random_sound = cache.get(cache_key)
    if not random_sound:
        random_sound = Sound.objects.random()
        cache.set(cache_key, random_sound, 60*60*24)
    return random_sound

def get_random_uploader():
    cache_key = "random_uploader"
    random_uploader = cache.get(cache_key)
    if not random_uploader:
        random_uploader = Profile.objects.random_uploader()
        cache.set(cache_key, random_uploader, 60*60*24)
    return random_uploader

def sounds(request):
    n_weeks_back = 51
    latest_sounds = Sound.objects.latest_additions(5, '3 years')
    latest_packs = Pack.objects.annotate(num_sounds=Count('sound'), last_update=Max('sound__created')).filter(num_sounds__gt=0).order_by("-last_update")[0:20]

    # popular_sounds = Sound.public.filter(download__created__gte=datetime.datetime.now()-datetime.timedelta(weeks=n_weeks_back)).annotate(num_d=Count('download')).order_by("-num_d")[0:20]
    popular_sounds = Sound.objects.filter(download__created__gte=datetime.datetime.now()-datetime.timedelta(weeks=n_weeks_back)).annotate(num_d=Count('download')).order_by("-num_d")[0:5]
    
    # popular_packs = Pack.objects.filter(sound__moderation_state="OK", sound__processing_state="OK").filter(download__created__gte=datetime.datetime.now()-datetime.timedelta(weeks=n_weeks_back)).annotate(num_d=Count('download')).order_by("-num_d")[0:20]
    popular_packs = Pack.objects.filter(download__created__gte=datetime.datetime.now()-datetime.timedelta(weeks=n_weeks_back)).annotate(num_d=Count('download')).order_by("-num_d")[0:20]
    
    random_sound = get_random_sound()
    random_uploader = get_random_uploader()
    return render_to_response('sounds/sounds.html', locals(), context_instance=RequestContext(request)) 

def remixed(request):
    pass

def random(request):
    pass

def packs(request):
    pass

def front_page(request):
    rss_url = settings.FREESOUND_RSS
    pledgie_campaign = settings.PLEDGIE_CAMPAIGN

    latest_forum_posts = Post.objects.select_related('author', 'thread', 'thread__forum').all().order_by("-created")[0:10]
    latest_additions = Sound.objects.latest_additions(5)
    
    random_sound = get_random_sound()
    
    return render_to_response('index.html', locals(), context_instance=RequestContext(request)) 


def sound(request, username, sound_id):
    try:
        sound = Sound.objects.select_related("license", "user", "pack").get(user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")
    except Sound.DoesNotExist: #@UndefinedVariable
        raise Http404
    
    tags = sound.tags.select_related("tag").all()

    content_type = ContentType.objects.get_for_model(Sound)

    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            sound.comments.add(Comment(content_object=sound, user=request.user, comment=form.cleaned_data["comment"]))
            #invalidate_template_cache()
            return HttpResponseRedirect(sound.get_absolute_url())
    else:
        form = CommentForm()

    qs = Comment.objects.select_related("user").filter(content_type=content_type, object_id=sound_id)

    return render_to_response('sounds/sound.html', combine_dicts(locals(), paginate(request, qs, settings.SOUND_COMMENTS_PER_PAGE)), context_instance=RequestContext(request))


@login_required
def sound_download(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")
    sound_path = sound.paths()["sound_path"] # 34/sounds/123_something.wav
    Download.objects.get_or_create(user=request.user, sound=sound)
    if settings.DEBUG:
        file_path = os.path.join(settings.SOUNDS_PATH, sound_path)
        wrapper = FileWrapper(file(file_path, "rb"))
        response = HttpResponse(wrapper, content_type='application/octet-stream')
        response['Content-Length'] = os.path.getsize(file_path)
        return response
    else:
        response = HttpResponse()
        response['Content-Type']="application/octet-stream"
        response['X-Accel-Redirect'] = os.path.join("/downloads/sounds/", sound_path)
        return response


@login_required
def pack_download(request, username, pack_id):
    pack = get_object_or_404(Pack, user__username__iexact=username, id=pack_id)
    pack_path = pack.base_filename_slug + '.zip'
    Download.objects.get_or_create(user=request.user, pack=pack)
    if settings.DEBUG:
        file_path = os.path.join(settings.PACKS_PATH, pack_path)
        wrapper = FileWrapper(file(file_path, "rb"))
        response = HttpResponse(wrapper, content_type='application/octet-stream')
        response['Content-Length'] = os.path.getsize(file_path)
        return response
    else:
        response = HttpResponse()
        response['Content-Type']="application/octet-stream"
        response['X-Accel-Redirect'] = os.path.join("downloads/packs/", pack_path)
        return response

        
@login_required
def sound_edit(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")
    
    if not (request.user.has_perm('sound.can_change') or sound.user == request.user):
        raise PermissionDenied
    
    def is_selected(prefix):
        if request.method == "POST":
            for name in request.POST.keys():
                if name.startswith(prefix + '-'):
                    return True
        return False
    
    if is_selected("description"):
        description_form = SoundDescriptionForm(request.POST, prefix="description")
        if description_form.is_valid():
            data = description_form.cleaned_data
            sound.set_tags(data["tags"])
            sound.description = data["description"]
            sound.save()
            invalidate_template_cache("sound_header", sound.id)
            return HttpResponseRedirect(sound.get_absolute_url())
    else:
        tags = " ".join([tagged_item.tag.name for tagged_item in sound.tags.all().order_by('tag__name')])
        description_form = SoundDescriptionForm(prefix="description", initial=dict(tags=tags, description=sound.description))
    
    packs = Pack.objects.filter(user=request.user)
    
    if is_selected("pack"):
        pack_form = PackForm(packs, request.POST, prefix="pack")
        if pack_form.is_valid():
            data = pack_form.cleaned_data
            if data['new_pack']:
                (pack, created) = Pack.objects.get_or_create(user=sound.user, name=data['new_pack'], name_slug=slugify(data['new_pack']))
                sound.pack = pack
            else:
                new_pack = data["pack"]
                old_pack = sound.pack
                if new_pack != old_pack:
                    if old_pack:
                        old_pack.is_dirty = True
                        old_pack.save()
                    if new_pack:
                        new_pack.is_dirty = True
                        new_pack.save()
                    sound.pack = new_pack
            sound.save()
            invalidate_template_cache("sound_header", sound.id)
            return HttpResponseRedirect(sound.get_absolute_url())
    else:
        pack_form = PackForm(packs, prefix="pack", initial=dict(pack=sound.pack.id) if sound.pack else None)

    if is_selected("geotag"):
        geotag_form = GeotaggingForm(request.POST, prefix="geotag")
        if geotag_form.is_valid():
            data = geotag_form.cleaned_data
            if data["remove_geotag"]:
                if sound.geotag:
                    geotag = sound.geotag.delete()
                    sound.geotag = None
                    sound.save()
            else:
                if sound.geotag:
                    sound.geotag.lat = data["lat"]
                    sound.geotag.lon = data["lon"]
                    sound.geotag.zoom = data["zoom"]
                else:
                    sound.geotag = GeoTag.objects.create(lat=data["lat"], lon=data["lon"], zoom=data["zoom"], user=request.user)
                    sound.save()
            
            invalidate_template_cache("sound_footer", sound.id)
            return HttpResponseRedirect(sound.get_absolute_url())    
    else:
        if sound.geotag:
            geotag_form = GeotaggingForm(prefix="geotag", initial=dict(lat=sound.geotag.lat, lon=sound.geotag.lon, zoom=sound.geotag.zoom))
        else:
            geotag_form = GeotaggingForm(prefix="geotag")

    if is_selected("license"):
        license_form = LicenseForm(request.POST, prefix="license")
        if license_form.is_valid():
            sound.license = license_form.cleaned_data["license"]
            sound.save()
            invalidate_template_cache("sound_footer", sound.id)
            return HttpResponseRedirect(sound.get_absolute_url())
    else:
        license_form = LicenseForm(prefix="license", initial=dict(license=sound.license.id))

    google_api_key = settings.GOOGLE_API_KEY
    
    return render_to_response('sounds/sound_edit.html', locals(), context_instance=RequestContext(request))

    
def remixes(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")
    qs = sound.remixes.filter(moderation_state="OK", processing_state="OK")
    return render_to_response('sounds/remixes.html', combine_dicts(locals(), paginate(request, qs, settings.SOUNDS_PER_PAGE)), context_instance=RequestContext(request))


def sources(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")
    qs = sound.sources.filter(moderation_state="OK", processing_state="OK")
    return render_to_response('sounds/sources.html', combine_dicts(locals(), paginate(request, qs, settings.SOUNDS_PER_PAGE)), context_instance=RequestContext(request))


def geotag(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")
    google_api_key = settings.GOOGLE_API_KEY
    return render_to_response('sounds/geotag.html', locals(), context_instance=RequestContext(request))


def similar(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")
    pass


def pack(request, username, pack_id):
    pack = get_object_or_404(Pack, user__username__iexact=username, id=pack_id)
    qs = Sound.objects.select_related('user').filter(pack=pack, moderation_state="OK", processing_state="OK")
    return render_to_response('sounds/pack.html', combine_dicts(locals(), paginate(request, qs, settings.SOUNDS_PER_PAGE)), context_instance=RequestContext(request))


def packs_for_user(request, username):
    user = get_object_or_404(User, username__iexact=username)
    order = request.GET.get("order", "name")
    if order not in ["name", "-last_update", "-created", "-num_sounds"]:
        order = "name"
    qs = Pack.objects.filter(user=user, sound__moderation_state="OK", sound__processing_state="OK").annotate(num_sounds=Count('sound'), last_update=Max('sound__created')).filter(num_sounds__gt=0).order_by(order)
    return render_to_response('sounds/packs.html', combine_dicts(paginate(request, qs, settings.PACKS_PER_PAGE), locals()), context_instance=RequestContext(request))


def for_user(request, username):
    user = get_object_or_404(User, username__iexact=username)
    qs = Sound.public.filter(user=user)
    return render_to_response('sounds/for_user.html', combine_dicts(paginate(request, qs, settings.SOUNDS_PER_PAGE), locals()), context_instance=RequestContext(request))
    

@login_required
def delete(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")
    
    if not (request.user.has_perm('sound.can_change') or sound.user == request.user):
        raise PermissionDenied

    import time
    
    encrypted_string = request.GET.get("sound", None)
     
    waited_too_long = False
    
    if encrypted_string != None:
        try:
            sound_id, now = decrypt(encrypted_string).split("\t")
            sound_id = int(sound_id)
            link_generated_time = float(now)
            
            if sound_id != sound.id:
                raise PermissionDenied
            
            if abs(time.time() - link_generated_time) < 10:
                sound.delete()
                return HttpResponseRedirect(reverse("accounts-home"))
            else:
                waited_too_long = True
        except:
            pass
    
    encrypted_link = encrypt(u"%d\t%f" % (sound.id, time.time()))
            
    return render_to_response('sounds/delete.html', locals(), context_instance=RequestContext(request))    


def flag(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")
    
    user = None
    email = None
    if request.user.is_authenticated():
        user = request.user
        email = request.user.email

    if request.method == "POST":
        flag_form = FlagForm(request.POST)
        if flag_form.is_valid():
            flag = flag_form.save(commit=False)
            flag.reporting_user=user
            flag.sound = sound
            flag.save()
            
            send_mail_template(u"[flag] flagged file", "sounds/email_flag.txt", dict(flag=flag), flag.email)

            return HttpResponseRedirect(sound.get_absolute_url())
    else:
        if user:
            flag_form = FlagForm(initial=dict(email=email))
        else:
            flag_form = FlagForm()
    
    return render_to_response('sounds/sound_flag.html', locals(), context_instance=RequestContext(request))