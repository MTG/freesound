from accounts.models import Profile
from comments.forms import CommentForm
from comments.models import Comment
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.core.cache import cache
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.servers.basehttp import FileWrapper
from django.core.urlresolvers import reverse
from django.db.models import Count, Max
from django.http import HttpResponseRedirect, Http404, HttpResponse, \
    HttpResponsePermanentRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from forum.models import Post
from freesound_exceptions import PermissionDenied
from geotags.models import GeoTag
from sounds.forms import SoundDescriptionForm, PackForm, GeotaggingForm, \
    NewLicenseForm, FlagForm, RemixForm
from accounts.models import Profile
from sounds.models import Sound, Pack, Download, RemixGroup
from tickets.models import Ticket, TicketComment
from tickets import TICKET_SOURCE_NEW_SOUND, TICKET_STATUS_CLOSED
from utils.cache import invalidate_template_cache
from utils.encryption import encrypt, decrypt
from utils.functional import combine_dicts
from utils.mail import send_mail_template
from utils.pagination import paginate
from utils.text import slugify
from utils.nginxsendfile import sendfile
import datetime, os, time, logging
from sounds.templatetags import display_sound
from django.db.models import Q
from utils.similarity_utilities import get_similar_sounds
import urllib
from django.contrib.sites.models import Site

logger = logging.getLogger('web')

sound_content_type = ContentType.objects.get_for_model(Sound)

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
    n_weeks_back = 1
    latest_sounds = Sound.objects.latest_additions(5, use_interval=False)
    latest_packs = Pack.objects.annotate(num_sounds=Count('sound'), last_update=Max('sound__created')).filter(num_sounds__gt=0).order_by("-last_update")[0:20]

    # popular_sounds = Sound.public.filter(download__created__gte=datetime.datetime.now()-datetime.timedelta(weeks=n_weeks_back)).annotate(num_d=Count('download')).order_by("-num_d")[0:20]
    popular_sounds = Sound.objects.filter(download__created__gte=datetime.datetime.now()-datetime.timedelta(weeks=n_weeks_back)).annotate(num_d=Count('download')).order_by("-num_d")[0:5]

    # popular_packs = Pack.objects.filter(sound__moderation_state="OK", sound__processing_state="OK").filter(download__created__gte=datetime.datetime.now()-datetime.timedelta(weeks=n_weeks_back)).annotate(num_d=Count('download')).order_by("-num_d")[0:20]
    popular_packs = Pack.objects.filter(download__created__gte=datetime.datetime.now()-datetime.timedelta(weeks=n_weeks_back)).annotate(num_d=Count('download')).order_by("-num_d")[0:20]

    random_sound = get_random_sound()
    random_uploader = get_random_uploader()
    return render_to_response('sounds/sounds.html', locals(), context_instance=RequestContext(request))

def remixed(request):
    qs = RemixGroup.objects.all().order_by('-group_size')
    return render_to_response('sounds/remixed.html', combine_dicts(locals(), paginate(request, qs, settings.SOUND_COMMENTS_PER_PAGE)), context_instance=RequestContext(request))


def random(request):
    sound_id = Sound.objects.random()
    if sound_id is None:
        raise Http404
    sound_obj = Sound.objects.get(pk=sound_id)
    return HttpResponseRedirect(reverse("sound",args=[sound_obj.user.username,sound_id])+"?random_browsing=true")


def packs(request):
    order = request.GET.get("order", "name")
    if order not in ["name", "-last_update", "-created", "-num_sounds", "-num_downloads"]:
        order = "name"
    qs = Pack.objects.select_related() \
                     .filter(sound__moderation_state="OK", sound__processing_state="OK") \
                     .annotate(num_sounds=Count('sound'), last_update=Max('sound__created')) \
                     .filter(num_sounds__gt=0) \
                     .order_by(order)
    return render_to_response('sounds/browse_packs.html',
                              combine_dicts(paginate(request, qs, settings.PACKS_PER_PAGE), locals()),
                              context_instance=RequestContext(request))


def front_page(request):
    rss_url = settings.FREESOUND_RSS
    pledgie_campaign = settings.PLEDGIE_CAMPAIGN
    latest_forum_posts = Post.objects.select_related('author', 'thread', 'thread__forum').all().order_by("-created")[0:10]
    latest_additions = Sound.objects.latest_additions(5, use_interval=False)
    random_sound = get_random_sound()
    return render_to_response('index.html', locals(), context_instance=RequestContext(request))


def sound(request, username, sound_id):
    try:
        sound = Sound.objects.select_related("license", "user", "user__profile", "pack", "remix_group").get(user__username__iexact=username, id=sound_id)
        user_is_owner = request.user.is_authenticated() and (sound.user == request.user or request.user.is_superuser or request.user.is_staff)
        # If the user is authenticated and this file is his, don't worry about moderation_state and processing_state
        if user_is_owner:
            if sound.moderation_state != "OK":
                messages.add_message(request, messages.INFO, 'Be advised, this file has <b>not been moderated</b> yet.')
            if sound.processing_state != "OK":
                messages.add_message(request, messages.INFO, 'Be advised, this file has <b>not been processed</b> yet.')
        else:
            if sound.moderation_state != 'OK' or sound.processing_state != 'OK':
                raise Http404
    except Sound.DoesNotExist: #@UndefinedVariable
        raise Http404

    tags = sound.tags.select_related("tag__name")

    if request.method == "POST":
        form = CommentForm(request, request.POST)
        if form.is_valid():
            comment_text=form.cleaned_data["comment"]
            sound.comments.add(Comment(content_object=sound, user=request.user, comment=comment_text))

            sound.num_comments = sound.num_comments + 1
            sound.save()
            try:
                # send the user an email to notify him of the new comment!
                print "Gonna send a mail to this user: %s" % request.user.email
                send_mail_template(
                    u'You have a new comment.', 'sounds/email_new_comment.txt',
                    {'sound': sound, 'user': request.user, 'comment': comment_text},
                    None, sound.user.email
                )
            except Exception, e:
                # if the email sending fails, ignore...
                print ("Problem sending email to '%s' about new comment: %s" \
                    % (request.user.email, e))

            return HttpResponseRedirect(sound.get_absolute_url())
    else:
        form = CommentForm(request)

    qs = Comment.objects.select_related("user", "user__profile").filter(content_type=sound_content_type, object_id=sound_id)
    display_random_link = request.GET.get('random_browsing')
    #facebook_like_link = urllib.quote_plus('http://%s%s' % (Site.objects.get_current().domain, reverse('sound', args=[sound.user.username, sound.id])))
    return render_to_response('sounds/sound.html', combine_dicts(locals(), paginate(request, qs, settings.SOUND_COMMENTS_PER_PAGE)), context_instance=RequestContext(request))

# N.B. login is required but adapted to not return the user to the download link.
def sound_download(request, username, sound_id):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('%s?next=%s' % (reverse("accounts-login"),
                                                    reverse("sound", args=[username, sound_id])))
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")
    Download.objects.get_or_create(user=request.user, sound=sound)
    return sendfile(sound.locations("path"), sound.friendly_filename(), sound.locations("sendfile_url"))

@login_required
def pack_download(request, username, pack_id):
    pack = get_object_or_404(Pack, user__username__iexact=username, id=pack_id)
    Download.objects.get_or_create(user=request.user, pack=pack)
    return sendfile(pack.locations("path"), pack.friendly_filename(), pack.locations("sendfile_url"))

@login_required
def sound_edit(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, processing_state='OK')

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
            sound.mark_index_dirty()
            invalidate_template_cache("sound_header", sound.id)
            # also update any possible related sound ticket
            tickets = Ticket.objects.filter(content__object_id=sound.id,
                                           source=TICKET_SOURCE_NEW_SOUND) \
                                   .exclude(status=TICKET_STATUS_CLOSED)
            for ticket in tickets:
                tc = TicketComment(sender=request.user,
                                   ticket=ticket,
                                   moderator_only=False,
                                   text='%s updated the sound description and/or tags.' % request.user.username)
                tc.save()
                ticket.send_notification_emails(ticket.NOTIFICATION_UPDATED,
                                                ticket.MODERATOR_ONLY)
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
                (pack, created) = Pack.objects.get_or_create(user=sound.user, name=data['new_pack'])
                if sound.pack:
                    sound.pack.is_dirty = True
                    sound.pack.save()
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
            sound.mark_index_dirty()
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
                    sound.mark_index_dirty()
            else:
                if sound.geotag:
                    sound.geotag.lat = data["lat"]
                    sound.geotag.lon = data["lon"]
                    sound.geotag.zoom = data["zoom"]
                else:
                    sound.geotag = GeoTag.objects.create(lat=data["lat"], lon=data["lon"], zoom=data["zoom"], user=request.user)
                    sound.mark_index_dirty()

            invalidate_template_cache("sound_footer", sound.id)
            return HttpResponseRedirect(sound.get_absolute_url())
    else:
        if sound.geotag:
            geotag_form = GeotaggingForm(prefix="geotag", initial=dict(lat=sound.geotag.lat, lon=sound.geotag.lon, zoom=sound.geotag.zoom))
        else:
            geotag_form = GeotaggingForm(prefix="geotag")

    license_form = NewLicenseForm(request.POST)
    if request.POST and license_form.is_valid():
        sound.license = license_form.cleaned_data["license"]
        sound.mark_index_dirty()
        invalidate_template_cache("sound_footer", sound.id)
        return HttpResponseRedirect(sound.get_absolute_url())
    else:
        license_form = NewLicenseForm({'license': sound.license})

    google_api_key = settings.GOOGLE_API_KEY

    return render_to_response('sounds/sound_edit.html', locals(), context_instance=RequestContext(request))


@login_required
def sound_edit_sources(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")

    if not (request.user.has_perm('sound.can_change') or sound.user == request.user):
        raise PermissionDenied

    current_sources = sound.sources.all()
    sources_string = ",".join(map(str, [source.id for source in current_sources]))

    remix_group = RemixGroup.objects.filter(sounds=current_sources)
    # No prints in production code!
    #print ("======== remix group id following ===========")
    #print (remix_group[0].id)

    if request.method == 'POST':
        form = RemixForm(sound, request.POST)
        if form.is_valid():
            form.save()
        else:
            # TODO: Don't use prints! Either use logging or return the error to the user. ~~ Vincent
            pass #print ("Form is not valid!!!!!!! %s" % ( form.errors))
    else:
        form = RemixForm(sound,initial=dict(sources=sources_string))
    return render_to_response('sounds/sound_edit_sources.html', locals(), context_instance=RequestContext(request))


def remixes(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")
    try:
        remix_group = sound.remix_groups.all()[0]
    except:
        raise Http404
    return HttpResponseRedirect(reverse("remix-group", args=[remix_group.id]))

def remix_group(request, group_id):
    group = get_object_or_404(RemixGroup, id=group_id)
    data = group.protovis_data
    sounds = group.sounds.all().order_by('created')
    last_sound = sounds[len(sounds)-1]
    group_sound = sounds[0]
    return render_to_response('sounds/remixes.html',
                              locals(),
                              context_instance=RequestContext(request))


def geotag(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")
    google_api_key = settings.GOOGLE_API_KEY
    return render_to_response('sounds/geotag.html', locals(), context_instance=RequestContext(request))


def similar(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username,
                              id=sound_id,
                              moderation_state="OK",
                              processing_state="OK")
                            #TODO: similarity_state="OK"
                            #TODO: this filter has to be added again, but first the db has to be updated

    similar_sounds = get_similar_sounds(sound,request.GET.get('preset', settings.DEFAULT_SIMILARITY_PRESET), int(settings.SOUNDS_PER_PAGE))
    logger.info('Got similar_sounds for %s: %s' % (sound_id, similar_sounds))
    return render_to_response('sounds/similar.html', locals(), context_instance=RequestContext(request))


def pack(request, username, pack_id):
    try:
        pack = Pack.objects.select_related().annotate(num_sounds=Count('sound')).get(user__username__iexact=username, id=pack_id)
    except Pack.DoesNotExist:
        raise Http404
    qs = Sound.objects.select_related('pack', 'user', 'license', 'geotag').filter(pack=pack, moderation_state="OK", processing_state="OK")
    return render_to_response('sounds/pack.html', combine_dicts(locals(), paginate(request, qs, settings.SOUNDS_PER_PAGE)), context_instance=RequestContext(request))


def packs_for_user(request, username):
    user = get_object_or_404(User, username__iexact=username)
    order = request.GET.get("order", "name")
    if order not in ["name", "-last_update", "-created", "-num_sounds", "-num_downloads"]:
        order = "name"
    qs = Pack.objects.select_related().filter(user=user, sound__moderation_state="OK", sound__processing_state="OK").annotate(num_sounds=Count('sound'), last_update=Max('sound__created')).filter(num_sounds__gt=0).order_by(order)
    return render_to_response('sounds/packs.html', combine_dicts(paginate(request, qs, settings.PACKS_PER_PAGE), locals()), context_instance=RequestContext(request))


def for_user(request, username):
    user = get_object_or_404(User, username__iexact=username)
    qs = Sound.public.filter(user=user)
    return render_to_response('sounds/for_user.html', combine_dicts(paginate(request, qs, settings.SOUNDS_PER_PAGE), locals()), context_instance=RequestContext(request))


@login_required
def delete(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")

    if not (request.user.has_perm('sound.delete_sound') or sound.user == request.user):
        raise PermissionDenied

    encrypted_string = request.GET.get("sound", None)

    waited_too_long = False

    if encrypted_string != None:
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


def __redirect_old_link(request, cls, url_name):
    obj_id = request.GET.get('id', False)
    if obj_id:
        try:
            obj = get_object_or_404(cls, id=int(obj_id))
            return HttpResponsePermanentRedirect(reverse(url_name, args=[obj.user.username, obj_id]))
        except ValueError:
            raise Http404
    else:
        raise Http404

def old_sound_link_redirect(request):
    return __redirect_old_link(request, Sound, "sound")

def old_pack_link_redirect(request):
    return __redirect_old_link(request, Pack, "pack")

def display_sound_wrapper(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id) #TODO: test the 404 case
    return render_to_response('sounds/display_sound.html', display_sound.display_sound(RequestContext(request), sound), context_instance=RequestContext(request))


def embed_iframe(request, sound_id, player_size):
    if player_size not in ['mini', 'small', 'medium', 'large']:
        raise Http404
    size = player_size
    sound = get_object_or_404(Sound, id=sound_id, moderation_state='OK', processing_state='OK')
    username_and_filename = '%s - %s' % (sound.user.username, sound.original_filename)
    return render_to_response('sounds/sound_iframe.html', locals(), context_instance=RequestContext(request))

def downloaders(request, username, sound_id):
    sound = Sound.objects.get(id=sound_id)
    # Retrieve all users that downloaded a sound
    qs = Download.objects.filter(sound=sound_id)
    num_results = len(qs)
    return render_to_response('sounds/downloaders.html', combine_dicts(paginate(request, qs, 32), locals()), context_instance=RequestContext(request))

def pack_downloaders(request, username, pack_id):
    pack = Pack.objects.get(id=pack_id)
    # Retrieve all users that downloaded a sound
    qs = Download.objects.filter(pack=pack_id)
    num_results = len(qs)
    return render_to_response('sounds/pack_downloaders.html', combine_dicts(paginate(request, qs, 32), locals()), context_instance=RequestContext(request))
