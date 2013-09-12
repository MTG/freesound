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

from accounts.models import Profile
from comments.forms import CommentForm
from comments.models import Comment
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.servers.basehttp import FileWrapper
from django.core.urlresolvers import reverse
from django.db import connection, transaction
from django.db.models import Count, Max, Q
from django.http import HttpResponseRedirect, Http404, HttpResponse, \
    HttpResponsePermanentRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from forum.models import Post, Thread
from freesound_exceptions import PermissionDenied
from geotags.models import GeoTag
from networkx import nx
from sounds.forms import SoundDescriptionForm, PackForm, GeotaggingForm, \
    NewLicenseForm, FlagForm, RemixForm, PackDescriptionForm
from sounds.management.commands.create_remix_groups import _create_nodes, \
    _create_and_save_remixgroup
from sounds.models import Sound, Pack, Download, RemixGroup, DeletedSound
from sounds.templatetags import display_sound
from tickets import TICKET_SOURCE_NEW_SOUND, TICKET_STATUS_CLOSED
from tickets.models import Ticket, TicketComment
from utils.cache import invalidate_template_cache
from utils.encryption import encrypt, decrypt
from utils.functional import combine_dicts
from utils.mail import send_mail_template
from utils.nginxsendfile import sendfile
from utils.pagination import paginate
from utils.similarity_utilities import get_similar_sounds
import datetime
import time
import logging
import json
import os

logger = logging.getLogger('web')
logger_click = logging.getLogger('clickusage')

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
    latest_sounds = Sound.objects.latest_additions(5, '2 days')
    latest_packs = Pack.objects.select_related().filter(sound__moderation_state="OK", sound__processing_state="OK").annotate(num_sounds=Count('sound'), last_update=Max('sound__created')).filter(num_sounds__gt=0).order_by("-last_update")[0:20]
    last_week = datetime.datetime.now()-datetime.timedelta(weeks=n_weeks_back)

    # N.B. this two queries group by twice on sound id, if anyone ever find out why....
    #popular_sounds = Download.objects.filter(created__gte=last_week)  \
    #                                 .exclude(sound=None)             \
    #                                 .values('sound_id')              \
    #                                 .annotate(num_d=Count('sound'))  \
    #                                 .order_by("-num_d")[0:5]
    popular_sounds = Sound.objects.filter(created__gte=last_week).order_by("-num_downloads")[0:5]


    packs = Download.objects.filter(created__gte=last_week)  \
                            .exclude(pack=None)              \
                            .values('pack_id')               \
                            .annotate(num_d=Count('pack'))   \
                            .order_by("-num_d")[0:5]

    #packs = []
    popular_packs = []                              
    for pack in packs:
        pack_obj = Pack.objects.select_related().get(id=pack['pack_id'])
        popular_packs.append({'pack': pack_obj,
                              'num_d': pack['num_d']
                              })
    
    random_sound = get_random_sound()
    random_uploader = get_random_uploader()
    return render_to_response('sounds/sounds.html', locals(), context_instance=RequestContext(request))


def remixed(request):
    # TODO: this doesn't return the right results after remix_group merge
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
                              combine_dicts(paginate(request, qs, settings.PACKS_PER_PAGE, cache_count=True), locals()),
                              context_instance=RequestContext(request))


def get_current_thread_ids():
    cursor = connection.cursor()
    cursor.execute("""
SELECT forum_thread.id
FROM forum_thread, forum_post
WHERE forum_thread.last_post_id = forum_post.id
ORDER BY forum_post.id DESC
LIMIT 10
""")
    return [x[0] for x in cursor.fetchall()]


def front_page(request):
    rss_cache = cache.get("rss_cache", None)
    pledgie_cache = cache.get("pledgie_cache", None)
    current_forum_threads = Thread.objects.filter(pk__in=get_current_thread_ids(),first_post__moderation_state="OK",last_post__moderation_state="OK") \
                                          .order_by('-last_post__created') \
                                          .select_related('author',
                                                          'thread',
                                                          'last_post', 'last_post__author', 'last_post__thread', 'last_post__thread__forum',
                                                          'forum', 'forum__name_slug')
    latest_additions = Sound.objects.latest_additions(5, '2 days')
    random_sound = get_random_sound()
    return render_to_response('index.html', locals(), context_instance=RequestContext(request))


def sound(request, username, sound_id):
    try:
        sound = Sound.objects.select_related("license", "user", "user__profile", "pack", "remix_group").get(user__username__iexact=username, id=sound_id)
        user_is_owner = request.user.is_authenticated() and (sound.user == request.user or request.user.is_superuser \
                        or request.user.is_staff or Group.objects.get(name='moderators') in request.user.groups.all())
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
        try:
            DeletedSound.objects.get(sound_id=sound_id)
            return render_to_response('sounds/deleted_sound.html', {}, context_instance=RequestContext(request))
        except DeletedSound.DoesNotExist:
            raise Http404

    tags = sound.tags.select_related("tag__name")

    if request.method == "POST":
        form = CommentForm(request, request.POST)
        if request.user.profile.is_blocked_for_spam_reports():
            messages.add_message(request, messages.INFO, "You're not allowed to post the comment because your account has been temporaly blocked after multiple spam reports")
        else:
            if form.is_valid():
                comment_text=form.cleaned_data["comment"]
                sound.comments.add(Comment(content_object=sound,
                                           user=request.user,
                                           comment=comment_text))
                sound.num_comments = sound.num_comments + 1
                sound.save()
                try:
                    # send the user an email to notify him of the new comment!
                    logger.debug("Notifying user %s of a new comment by %s" % (sound.user.username, request.user.username))
                    send_mail_template(u'You have a new comment.', 'sounds/email_new_comment.txt',
                                       {'sound': sound, 'user': request.user, 'comment': comment_text},
                                       None, sound.user.email)
                except Exception, e:
                    # if the email sending fails, ignore...
                    logger.error("Problem sending email to '%s' about new comment: %s" \
                                 % (request.user.email, e))

                return HttpResponseRedirect(sound.get_absolute_url())
    else:
        form = CommentForm(request)

    qs = Comment.objects.select_related("user", "user__profile").filter(content_type=sound_content_type, object_id=sound_id)
    display_random_link = request.GET.get('random_browsing')
    do_log = settings.LOG_CLICKTHROUGH_DATA

    #facebook_like_link = urllib.quote_plus('http://%s%s' % (Site.objects.get_current().domain, reverse('sound', args=[sound.user.username, sound.id])))
    return render_to_response('sounds/sound.html', combine_dicts(locals(), paginate(request, qs, settings.SOUND_COMMENTS_PER_PAGE)), context_instance=RequestContext(request))


def sound_download(request, username, sound_id):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('%s?next=%s' % (reverse("accounts-login"),
                                                    reverse("sound", args=[username, sound_id])))   
    if settings.LOG_CLICKTHROUGH_DATA:
        click_log(request,click_type='sounddownload',sound_id=sound_id)
    
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")
    Download.objects.get_or_create(user=request.user, sound=sound)
    return sendfile(sound.locations("path"), sound.friendly_filename(), sound.locations("sendfile_url"))


def sound_preview(request, folder_id, sound_id, user_id):

    if settings.LOG_CLICKTHROUGH_DATA:
        click_log(request,click_type='soundpreview',sound_id=sound_id)

    url = request.get_full_path().replace("data/previews_alt/","data/previews/")
    return HttpResponseRedirect(url)


def pack_download(request, username, pack_id):
    from django.http import HttpResponse

    if not request.user.is_authenticated():
        return HttpResponseRedirect('%s?next=%s' % (reverse("accounts-login"),
                                                    reverse("pack", args=[username, pack_id])))
        
    if settings.LOG_CLICKTHROUGH_DATA:
        click_log(request,click_type='packdownload',pack_id=pack_id)
        
    pack = get_object_or_404(Pack, user__username__iexact=username, id=pack_id)
    Download.objects.get_or_create(user=request.user, pack=pack)

    filelist =  "%s %i %s %s\r\n" % (pack.license_crc,os.stat(pack.locations('license_path')).st_size, pack.locations('license_url'), "_readme_and_license.txt")
    for sound in pack.sound_set.filter(processing_state="OK", moderation_state="OK"):
        url = sound.locations("sendfile_url")
        name = sound.friendly_filename()
        if sound.crc=='': continue
        filelist = filelist + "%s %i %s %s\r\n"%(sound.crc, sound.filesize,url,name)
    response = HttpResponse(filelist, content_type="text/plain")
    response['X-Archive-Files']='zip'
    return response


@login_required
def sound_edit(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, processing_state='OK')

    if not (request.user.has_perm('sound.can_change') or sound.user == request.user):
        raise PermissionDenied

    def invalidate_sound_cache(sound):
        invalidate_template_cache("sound_header", sound.id, True)
        invalidate_template_cache("sound_header", sound.id, False)
        invalidate_template_cache("sound_footer_top", sound.id)
        invalidate_template_cache("sound_footer_bottom", sound.id)
        invalidate_template_cache("display_sound", sound.id, True, sound.processing_state, sound.moderation_state)
        invalidate_template_cache("display_sound", sound.id, False, sound.processing_state, sound.moderation_state)

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
            sound.original_filename = data["name"]
            sound.mark_index_dirty()
            invalidate_sound_cache(sound)
            
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
        description_form = SoundDescriptionForm(prefix="description",
                                                initial=dict(tags=tags,
                                                             description=sound.description,
                                                             name=sound.original_filename))

    packs = Pack.objects.filter(user=request.user)

    if is_selected("pack"):
        pack_form = PackForm(packs, request.POST, prefix="pack")
        if pack_form.is_valid():
            data = pack_form.cleaned_data
            dirty_packs = []
            if data['new_pack']:
                (pack, created) = Pack.objects.get_or_create(user=sound.user, name=data['new_pack'])
                sound.pack = pack
            else:
                new_pack = data["pack"]
                old_pack = sound.pack
                if new_pack != old_pack:
                    sound.pack = new_pack
                if new_pack:
                    dirty_packs.append(new_pack)
                if old_pack:
                    dirty_packs.append(old_pack)

            for p in dirty_packs:
               p.process()

            sound.mark_index_dirty()
            invalidate_sound_cache(sound)
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
                    sound.geotag.save()
                else:
                    sound.geotag = GeoTag.objects.create(lat=data["lat"], lon=data["lon"], zoom=data["zoom"], user=request.user)
                    sound.mark_index_dirty()

            invalidate_sound_cache(sound)
            
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
        invalidate_sound_cache(sound)
        return HttpResponseRedirect(sound.get_absolute_url())
    else:
        license_form = NewLicenseForm(initial={'license': sound.license})
    
    google_api_key = settings.GOOGLE_API_KEY

    return render_to_response('sounds/sound_edit.html', locals(), context_instance=RequestContext(request))


@login_required
def sound_edit_sources(request, username, sound_id):
    print "=========== SOUND_ID: " + sound_id
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
            # FIXME: temp solution to not fuckup the deployment in tabasco
            # remix_group = RemixGroup.objects.filter(sounds=sound) 
            # if remix_group:
            #     __recalc_remixgroup(remix_group[0], sound)
        else:
            # TODO: Don't use prints! Either use logging or return the error to the user. ~~ Vincent
            pass #print ("Form is not valid!!!!!!! %s" % ( form.errors))
    else:
        form = RemixForm(sound,initial=dict(sources=sources_string))
    return render_to_response('sounds/sound_edit_sources.html', locals(), context_instance=RequestContext(request))

# TODO: handle case were added/removed sound is part of remixgroup
def __recalc_remixgroup(remixgroup, sound):

    # recreate remixgroup
    dg = nx.DiGraph()
    data = json.loads(remixgroup.networkx_data)
    dg.add_nodes_from(data['nodes'])
    dg.add_edges_from(data['edges'])
    
    # print "========= NODES =========="
    print dg.nodes()
    # print "========= EDGES =========="
    print dg.edges()
    
    # add new nodes/edges (sources in this case)
    for source in sound.sources.all():
        if source.id not in dg.successors(sound.id) \
                    and source.created < sound.created: # time-bound, avoid illegal source assignment
            dg.add_node(source.id)
            dg.add_edge(sound.id, source.id)
            remix_group = RemixGroup.objects.filter(sounds=source)
            if remix_group:
                dg = __nested_remixgroup(dg, remix_group[0])
            
    try:
        # remove old nodes/edges
        for source in dg.successors(sound.id):
            if source not in [s.id for s in sound.sources.all()]:
                dg.remove_node(source) # TODO: check if edges are removed automatically
        
        # create and save the modified remixgroup
        dg = _create_nodes(dg)
        print "============ NODES AND EDGES =============="
        print dg.nodes()
        print dg.edges()
        _create_and_save_remixgroup(dg, remixgroup)
    except Exception, e:
        logger.warning(e)    

def __nested_remixgroup(dg1, remix_group):
    print "============= nested remix_group ================ \n"
    dg2 = nx.DiGraph()
    data = json.loads(remix_group.networkx_data)
    dg2.add_nodes_from(data['nodes'])
    dg2.add_edges_from(data['edges'])
        
    print "========== MERGED GROUP NODES: " + str(dg1.nodes())

    # FIXME: this combines the graphs correctly
    #        recheck the time-bound concept
    dg1 = nx.compose(dg1, dg2)
    print dg1.nodes()

    return dg1

def remixes(request, username, sound_id):
    sound = get_object_or_404(Sound, user__username__iexact=username, id=sound_id, moderation_state="OK", processing_state="OK")
    try:
        remix_group = sound.remix_group.all()[0]
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
                              processing_state="OK",
                              analysis_state="OK",
                              similarity_state="OK")

    similar_sounds = get_similar_sounds(sound,request.GET.get('preset', None), int(settings.SOUNDS_PER_PAGE))
    logger.debug('Got similar_sounds for %s: %s' % (sound_id, similar_sounds))
    return render_to_response('sounds/similar.html', locals(), context_instance=RequestContext(request))


def pack(request, username, pack_id):
    try:
        pack = Pack.objects.select_related().annotate(num_sounds=Count('sound')).get(user__username__iexact=username, id=pack_id)
    except Pack.DoesNotExist:
        raise Http404
    qs = Sound.objects.select_related('pack', 'user', 'license', 'geotag').filter(pack=pack, moderation_state="OK", processing_state="OK")
    num_sounds_ok = len(qs)
    # TODO: refactor: This list of geotags is only used to determine if we need to show the geotag map or not
    pack_geotags = Sound.public.select_related('license', 'pack', 'geotag', 'user', 'user__profile').filter(pack=pack).exclude(geotag=None).exists()
    google_api_key = settings.GOOGLE_API_KEY
    
    if num_sounds_ok == 0 and pack.num_sounds != 0:
        messages.add_message(request, messages.INFO, 'The sounds of this pack have <b>not been moderated</b> yet.')
    else :
        if num_sounds_ok < pack.num_sounds :
            messages.add_message(request, messages.INFO, 'This pack contains more sounds that have <b>not been moderated</b> yet.')

    # If user is owner of pack, display form to add description
    enable_description_form = False
    if request.user.username == username:
        enable_description_form = True
        form = PackDescriptionForm(instance = pack)

    # Manage POST info (if adding a description)
    if request.method == 'POST':
        form = PackDescriptionForm(request.POST, pack)
        if form.is_valid():
            pack.description = form.cleaned_data['description']
            pack.save()
        else:
            pass

    file_exists = os.path.exists(pack.locations("license_path"))

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
            logger.debug("User %s requested to delete sound %s" % (request.user.username,sound_id))
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
        flag_form = FlagForm(request, request.POST)
        if flag_form.is_valid():
            flag = flag_form.save()
            flag.reporting_user=user
            flag.sound = sound
            flag.save()

            send_mail_template(u"[flag] flagged file", "sounds/email_flag.txt", dict(flag=flag), flag.email)

            return HttpResponseRedirect(sound.get_absolute_url())
    else:
        if user:
            flag_form = FlagForm(request,initial=dict(email=email))
        else:
            flag_form = FlagForm(request)

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
    if player_size not in ['mini', 'small', 'medium', 'large', 'large_no_info']:
        raise Http404
    size = player_size
    sound = get_object_or_404(Sound, id=sound_id, moderation_state='OK', processing_state='OK')
    username_and_filename = '%s - %s' % (sound.user.username, sound.original_filename)
    return render_to_response('sounds/sound_iframe.html', locals(), context_instance=RequestContext(request))

def downloaders(request, username, sound_id):
    sound = get_object_or_404(Sound, id=sound_id)
    
    # Retrieve all users that downloaded a sound
    qs = Download.objects.filter(sound=sound_id)
    return render_to_response('sounds/downloaders.html', combine_dicts(paginate(request, qs, 32), locals()), context_instance=RequestContext(request))

def pack_downloaders(request, username, pack_id):
    pack = get_object_or_404(Pack, id = pack_id)
    
    # Retrieve all users that downloaded a sound
    qs = Download.objects.filter(pack=pack_id)
    return render_to_response('sounds/pack_downloaders.html', combine_dicts(paginate(request, qs, 32), locals()), context_instance=RequestContext(request))

def click_log(request,click_type=None, sound_id="", pack_id="" ):
    
    searchtime_session_key = request.session.get("searchtime_session_key", "")
    authenticated_session_key = ""
    if request.user.is_authenticated():
        authenticated_session_key = request.session.session_key
    if click_type in ['soundpreview', 'sounddownload']:
        entity_id = sound_id
    else:
        entity_id = pack_id

    logger_click.info("%s : %s : %s : %s"
                          % (click_type, authenticated_session_key, searchtime_session_key, unicode(entity_id).encode('utf-8')))
