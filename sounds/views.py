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
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse, resolve
from django.db import connection, transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, Http404,\
    HttpResponsePermanentRedirect, JsonResponse
from django.shortcuts import render, get_object_or_404, render, redirect
from django.utils.six.moves.urllib.parse import urlparse
from django.http import HttpResponse
from django.template import loader
from accounts.models import Profile
from comments.forms import CommentForm
from comments.models import Comment
from forum.models import Thread
from freesound.freesound_exceptions import PermissionDenied
from geotags.models import GeoTag
from sounds.forms import *
from sounds.management.commands.create_remix_groups import _create_nodes, _create_and_save_remixgroup
from sounds.models import Sound, Pack, License, Download, RemixGroup, DeletedSound, SoundOfTheDay, SoundLicenseHistory
from sounds.templatetags import display_sound
from donations.models import DonationsModalSettings
from tickets import TICKET_STATUS_CLOSED
from utils.search.search_general import get_random_sound_from_solr
from tickets.models import Ticket, TicketComment
from utils.downloads import download_sounds, should_suggest_donation
from utils.encryption import encrypt, decrypt
from utils.functional import combine_dicts
from utils.mail import send_mail_template
from utils.nginxsendfile import sendfile
from utils.pagination import paginate
from utils.similarity_utilities import get_similar_sounds
from utils.text import remove_control_chars
from follow import follow_utils
from operator import itemgetter
import gearman
import datetime
import time
import logging
import json
import os


logger = logging.getLogger('web')


def get_sound_of_the_day_id():
    """
    Returns random id of sound (int)
    """
    cache_key = "random_sound"
    random_sound = cache.get(cache_key)
    if not random_sound:
        try:
            today = datetime.date.today()
            now = datetime.datetime.now()
            tomorrow = datetime.datetime(today.year, today.month, today.day)
            time_until_tomorrow = tomorrow - now

            rnd = SoundOfTheDay.objects.get(date_display=today)
            random_sound = rnd.sound_id
            # Set the cache to expire at midnight tomorrow, so that
            # a new sound is chosen
            cache.set(cache_key, random_sound, time_until_tomorrow.seconds)
        except SoundOfTheDay.DoesNotExist:
            return None
    return random_sound


def sounds(request):
    n_weeks_back = 1
    latest_sounds = Sound.objects.latest_additions(5, '2 days')
    latest_sound_objects = Sound.objects.ordered_ids([latest_sound['sound_id'] for latest_sound in latest_sounds])
    latest_sounds = [(latest_sound, latest_sound_objects[index],) for index, latest_sound in enumerate(latest_sounds)]
    latest_packs = Pack.objects.select_related().filter(num_sounds__gt=0).exclude(is_deleted=True).order_by("-last_updated")[0:20]
    last_week = datetime.datetime.now()-datetime.timedelta(weeks=n_weeks_back)
    popular_sound_ids = [snd.id for snd in Sound.objects.filter(\
            Q(moderation_date__gte=last_week) | Q(created__gte=last_week)).order_by("-num_downloads")[0:5]]
    popular_sounds = Sound.objects.ordered_ids(popular_sound_ids)
    popular_packs = Pack.objects.filter(created__gte=last_week).exclude(is_deleted=True).order_by("-num_downloads")[0:5]
    random_sound_id = get_sound_of_the_day_id()
    if random_sound_id:
        random_sound = Sound.objects.bulk_query_id([random_sound_id])[0]
    else:
        random_sound = None
    tvars = {
        'latest_sounds': latest_sounds,
        'latest_packs': latest_packs,
        'popular_sounds': popular_sounds,
        'popular_packs': popular_packs,
        'random_sound': random_sound
    }
    return render(request, 'sounds/sounds.html', tvars)


def remixed(request):
    qs = RemixGroup.objects.all().order_by('-group_size')
    tvars = dict()
    tvars.update(paginate(request, qs, settings.SOUND_COMMENTS_PER_PAGE))
    return render(request, 'sounds/remixed.html', tvars)


def random(request):
    sound = get_random_sound_from_solr()
    sound_obj = None
    if sound:
        try:
            # There is a small edge case where a sound may have been marked
            # as explicit and is selected here before the index is updated,
            # but we expect this to happen rarely enough that it's not a problem
            sound_obj = Sound.objects.get(id=sound['id'])
        except Sound.DoesNotExist:
            pass
    if sound_obj is None:
        # Only if solr is down - Won't happen very often, but Sound.objects.random
        # will also restrict by sounds with at least 3 ratings  and an average
        # rating of >6. Not important to change this for the rare case that we trigger this.
        try:
            sound_obj = Sound.objects.random()
        except Sound.DoesNotExist:
            pass
    if sound_obj is None:
        raise Http404
    return HttpResponseRedirect('{}?random_browsing=true'.format(
        reverse('sound', args=[sound_obj.user.username, sound_obj.id])))


def packs(request):
    order = request.GET.get("order", "name")
    if order not in ["name", "-last_updated", "-created", "-num_sounds", "-num_downloads"]:
        order = "name"
    qs = Pack.objects.select_related() \
                     .filter(num_sounds__gt=0) \
                     .exclude(is_deleted=True) \
                     .order_by(order)
    tvars = {'order': order}
    tvars.update(paginate(request, qs, settings.PACKS_PER_PAGE, cache_count=True))
    return render(request, 'sounds/browse_packs.html', tvars)


def get_current_thread_ids():
    cursor = connection.cursor()
    cursor.execute("""
          SELECT forum_thread.id
            FROM forum_thread, forum_post
           WHERE forum_thread.last_post_id = forum_post.id
        ORDER BY forum_post.id DESC LIMIT 10
    """)
    return [x[0] for x in cursor.fetchall()]


def front_page(request):
    rss_cache = cache.get("rss_cache", None)
    donations_cache = cache.get("donations_cache", None)
    current_forum_threads = Thread.objects.filter(pk__in=get_current_thread_ids(),
                                                  first_post__moderation_state="OK",
                                                  last_post__moderation_state="OK") \
                                          .order_by('-last_post__created') \
                                          .select_related('author',
                                                          'forum',
                                                          'last_post',
                                                          'last_post__author',
                                                          'last_post__thread',
                                                          'last_post__thread__forum')
    latest_additions = Sound.objects.latest_additions(5, '2 days')
    random_sound_id = get_sound_of_the_day_id()
    if random_sound_id:
        random_sound = Sound.objects.bulk_query_id([random_sound_id])[0]
    else:
        random_sound = None
    tvars = {
        'rss_cache': rss_cache,
        'donations_cache': donations_cache,
        'current_forum_threads': current_forum_threads,
        'latest_additions': latest_additions,
        'random_sound': random_sound
    }
    return render(request, 'index.html', tvars)


def sound(request, username, sound_id):
    try:
        sound = Sound.objects.select_related("license", "user", "user__profile", "pack").get(id=sound_id)
        if sound.user.username.lower() != username.lower():
            raise Http404
        user_is_owner = request.user.is_authenticated and \
            (sound.user == request.user or request.user.is_superuser or request.user.is_staff or
             Group.objects.get(name='moderators') in request.user.groups.all())
        # If the user is authenticated and this file is his, don't worry about moderation_state and processing_state
        if user_is_owner:
            if sound.moderation_state != "OK":
                messages.add_message(request, messages.INFO, 'Be advised, this file has <b>not been moderated</b> yet.')
            if sound.processing_state != "OK":
                messages.add_message(request, messages.INFO, 'Be advised, this file has <b>not been processed</b> yet.')
        else:
            if sound.moderation_state != 'OK' or sound.processing_state != 'OK':
                raise Http404
    except Sound.DoesNotExist:
        if DeletedSound.objects.filter(sound_id=sound_id).exists():
            return render(request, 'sounds/deleted_sound.html')
        else:
            raise Http404

    if request.method == "POST":
        form = CommentForm(request, request.POST)
        if request.user.is_authenticated:
            if request.user.profile.is_blocked_for_spam_reports():
                messages.add_message(request, messages.INFO, "You're not allowed to post the comment because your account "
                                                             "has been temporaly blocked after multiple spam reports")
            else:
                if form.is_valid():
                    comment_text = form.cleaned_data["comment"]
                    sound.add_comment(request.user, comment_text)
                    try:
                        if request.user.profile.email_not_disabled("new_comment"):
                            # Send the user an email to notify him of the new comment!
                            logger.debug("Notifying user %s of a new comment by %s" % (sound.user.username,
                                                                                       request.user.username))
                            send_mail_template(u'You have a new comment.', 'sounds/email_new_comment.txt',
                                               {'sound': sound, 'user': request.user, 'comment': comment_text},
                                               None, sound.user.email)
                    except Exception as e:
                        # If the email sending fails, ignore...
                        logger.error("Problem sending email to '%s' about new comment: %s" % (request.user.email, e))

                    return HttpResponseRedirect(sound.get_absolute_url())
    else:
        form = CommentForm(request)

    qs = Comment.objects.select_related("user", "user__profile")\
        .filter(sound_id=sound_id)
    display_random_link = request.GET.get('random_browsing')
    is_following = False
    if request.user.is_authenticated:
        users_following = follow_utils.get_users_following(request.user)
        if sound.user in users_following:
            is_following = True
    is_explicit = sound.is_explicit and (not request.user.is_authenticated \
                        or not request.user.profile.is_adult)


    tvars = {
        'sound': sound,
        'username': username,
        'form': form,
        'display_random_link': display_random_link,
        'is_following': is_following,
        'is_explicit': is_explicit,
        'sizes': settings.IFRAME_PLAYER_SIZE,
    }
    tvars.update(paginate(request, qs, settings.SOUND_COMMENTS_PER_PAGE))
    return render(request, 'sounds/sound.html', tvars)


@login_required
def after_download_modal(request):
    """
    This view checks if a modal should be shown after the user has downloaded a sound, and returns either the contents
    of the modal if needed.
    """
    response_content = None  # Default content of the response set to None (no modal)
    sound_name = request.GET.get('sound_name', 'this sound')  # Gets some data sent by the client

    def modal_shown_timestamps_cache_key(user):
        return 'modal_shown_timestamps_donations_shown_%i' % user.id

    if DonationsModalSettings.get_donation_modal_settings().enabled:
        # Get timestamps of last times modal was shown from cache
        modal_shown_timestamps = cache.get(modal_shown_timestamps_cache_key(request.user), [])

        # Iterate over timestamps, keep only the ones in last 24 hours and do the counting
        modal_shown_timestamps = [item for item in modal_shown_timestamps if item > (time.time() - 24 * 3600)]

        if should_suggest_donation(request.user, len(modal_shown_timestamps)):
            logger.info('Showing after download donate modal (%s)' % json.dumps({'user_id': request.user.id}))
            modal_shown_timestamps.append(time.time())
            cache.set(modal_shown_timestamps_cache_key(request.user), modal_shown_timestamps)
            template = loader.get_template('sounds/after_download_modal_donation.html')
            response_content = template.render({'sound_name': sound_name})

    return JsonResponse({'content': response_content})

@transaction.atomic()
def sound_download(request, username, sound_id):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('%s?next=%s' % (reverse("accounts-login"),
                                                    reverse("sound", args=[username, sound_id])))
    sound = get_object_or_404(Sound, id=sound_id, moderation_state="OK", processing_state="OK")
    if sound.user.username.lower() != username.lower():
        raise Http404
    if not Download.objects.filter(user=request.user, sound=sound).exists():
        Download.objects.create(user=request.user, sound=sound, license=sound.license)
    return sendfile(sound.locations("path"), sound.friendly_filename(), sound.locations("sendfile_url"))


def pack_download(request, username, pack_id):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('%s?next=%s' % (reverse("accounts-login"),
                                                    reverse("pack", args=[username, pack_id])))
    pack = get_object_or_404(Pack, id=pack_id)
    if pack.user.username.lower() != username.lower():
        raise Http404
    if not Download.objects.filter(user=request.user, pack=pack).exists():
        Download.objects.create(user=request.user, pack=pack)
    licenses_url = (reverse('pack-licenses', args=[username, pack_id]))
    return download_sounds(licenses_url, pack)


def pack_licenses(request, username, pack_id):
    pack = get_object_or_404(Pack, id=pack_id)
    attribution = pack.get_attribution()
    return HttpResponse(attribution, content_type="text/plain")


@login_required
@transaction.atomic()
def sound_edit(request, username, sound_id):
    sound = get_object_or_404(Sound, id=sound_id, processing_state='OK')
    if sound.user.username.lower() != username.lower():
        raise Http404

    if not (request.user.has_perm('sound.can_change') or sound.user == request.user):
        raise PermissionDenied

    def is_selected(prefix):
        if request.method == "POST":
            for name in request.POST.keys():
                if name.startswith(prefix + '-'):
                    return True
        return False

    def update_sound_tickets(sound, text):
        tickets = Ticket.objects.filter(sound_id=sound.id)\
                               .exclude(status=TICKET_STATUS_CLOSED)
        for ticket in tickets:
            tc = TicketComment(sender=request.user,
                               ticket=ticket,
                               moderator_only=False,
                               text=text)
            tc.save()
            ticket.send_notification_emails(ticket.NOTIFICATION_UPDATED,
                                            ticket.MODERATOR_ONLY)

    if is_selected("description"):
        description_form = SoundDescriptionForm(
                request.POST,
                prefix="description",
                explicit_disable=sound.is_explicit)

        if description_form.is_valid():
            data = description_form.cleaned_data
            sound.is_explicit = data["is_explicit"]
            sound.set_tags(data["tags"])
            sound.description = remove_control_chars(data["description"])
            sound.original_filename = data["name"]
            sound.mark_index_dirty()
            sound.invalidate_template_caches()
            update_sound_tickets(sound, '%s updated the sound description and/or tags.' % request.user.username)
            return HttpResponseRedirect(sound.get_absolute_url())
    else:
        tags = " ".join([tagged_item.tag.name for tagged_item in sound.tags.all().order_by('tag__name')])
        description_form = SoundDescriptionForm(prefix="description",
                                                explicit_disable=sound.is_explicit,
                                                initial=dict(tags=tags,
                                                             description=sound.description,
                                                             name=sound.original_filename))

    packs = Pack.objects.filter(user=request.user).exclude(is_deleted=True)
    if is_selected("pack"):
        pack_form = PackForm(packs, request.POST, prefix="pack")
        if pack_form.is_valid():
            data = pack_form.cleaned_data
            affected_packs = []
            if data['new_pack']:
                (pack, created) = Pack.objects.get_or_create(user=sound.user, name=data['new_pack'])
                if sound.pack:
                    affected_packs.append(sound.pack)  # Append previous sound pack if exists
                sound.pack = pack
                affected_packs.append(pack)
            else:
                new_pack = data["pack"]
                old_pack = sound.pack
                if new_pack != old_pack:
                    sound.pack = new_pack
                    if new_pack:
                        affected_packs.append(new_pack)
                    if old_pack:
                        affected_packs.append(old_pack)

            sound.mark_index_dirty()  # Marks as dirty and saves
            sound.invalidate_template_caches()
            update_sound_tickets(sound, '%s updated the sound pack.' % request.user.username)
            for affected_pack in affected_packs:  # Process affected packs
                affected_pack.process()

            return HttpResponseRedirect(sound.get_absolute_url())
    else:
        pack_form = PackForm(packs, prefix="pack", initial=dict(pack=sound.pack.id) if sound.pack else None)

    if is_selected("geotag"):
        geotag_form = GeotaggingForm(request.POST, prefix="geotag")
        if geotag_form.is_valid():
            data = geotag_form.cleaned_data
            if data["remove_geotag"]:
                if sound.geotag:
                    sound.geotag.delete()
                    sound.geotag = None
                    sound.mark_index_dirty()
            else:
                if sound.geotag:
                    sound.geotag.lat = data["lat"]
                    sound.geotag.lon = data["lon"]
                    sound.geotag.zoom = data["zoom"]
                    sound.geotag.save()
                else:
                    sound.geotag = GeoTag.objects.create(lat=data["lat"], lon=data["lon"], zoom=data["zoom"],
                                                         user=request.user)
                    sound.mark_index_dirty()

            sound.mark_index_dirty()
            sound.invalidate_template_caches()
            update_sound_tickets(sound, '%s updated the sound geotag.' % request.user.username)
            return HttpResponseRedirect(sound.get_absolute_url())
    else:
        if sound.geotag:
            geotag_form = GeotaggingForm(prefix="geotag", initial=dict(lat=sound.geotag.lat, lon=sound.geotag.lon,
                                                                       zoom=sound.geotag.zoom))
        else:
            geotag_form = GeotaggingForm(prefix="geotag")

    license_form = NewLicenseForm(request.POST)
    if request.POST and license_form.is_valid():
        new_license = license_form.cleaned_data["license"]
        if new_license != sound.license:
            sound.set_license(new_license)
        sound.mark_index_dirty()  # Sound is saved here
        if sound.pack:
            sound.pack.process()  # Sound license changed, process pack (if sound has pack)
        sound.invalidate_template_caches()
        update_sound_tickets(sound, '%s updated the sound license.' % request.user.username)
        return HttpResponseRedirect(sound.get_absolute_url())
    else:
        license_form = NewLicenseForm(initial={'license': sound.license})

    tvars = {
        'sound': sound,
        'description_form': description_form,
        'pack_form': pack_form,
        'geotag_form': geotag_form,
        'license_form': license_form
    }
    return render(request, 'sounds/sound_edit.html', tvars)


@login_required
def pack_edit(request, username, pack_id):
    pack = get_object_or_404(Pack, id=pack_id)
    if pack.user.username.lower() != username.lower():
        raise Http404
    pack_sounds = ",".join([str(s.id) for s in pack.sound_set.all()])

    if not (request.user.has_perm('pack.can_change') or pack.user == request.user):
        raise PermissionDenied

    current_sounds = list()
    if request.method == "POST":
        form = PackEditForm(request.POST, instance=pack)
        if form.is_valid():
            form.save()
            pack.sound_set.all().update(is_index_dirty=True)
            return HttpResponseRedirect(pack.get_absolute_url())
    else:
        form = PackEditForm(instance=pack, initial=dict(pack_sounds=pack_sounds))
        current_sounds = Sound.objects.bulk_sounds_for_pack(pack_id=pack.id)
    tvars = {
        'pack': pack,
        'form': form,
        'current_sounds': current_sounds,
    }
    return render(request, 'sounds/pack_edit.html', tvars)


@login_required
def pack_delete(request, username, pack_id):
    pack = get_object_or_404(Pack, id=pack_id)
    if pack.user.username.lower() != username.lower():
        raise Http404

    if not (request.user.has_perm('pack.can_change') or pack.user == request.user):
        raise PermissionDenied

    encrypted_string = request.GET.get("pack", None)
    waited_too_long = False
    if encrypted_string is not None:
        pack_id, now = decrypt(encrypted_string).split("\t")
        pack_id = int(pack_id)
        link_generated_time = float(now)
        if pack_id != pack.id:
            raise PermissionDenied
        if abs(time.time() - link_generated_time) < 10:
            logger.debug("User %s requested to delete pack %s" % (request.user.username, pack_id))
            pack.delete_pack(remove_sounds=False)
            return HttpResponseRedirect(reverse("accounts-home"))
        else:
            waited_too_long = True

    encrypted_link = encrypt(u"%d\t%f" % (pack.id, time.time()))
    tvars = {
        'pack': pack,
        'encrypted_link': encrypted_link,
        'waited_too_long': waited_too_long
    }
    return render(request, 'sounds/pack_delete.html', tvars)


@login_required
def sound_edit_sources(request, username, sound_id):
    sound = get_object_or_404(Sound, id=sound_id)
    if sound.user.username.lower() != username.lower():
        raise Http404

    if not (request.user.has_perm('sound.can_change') or sound.user == request.user):
        raise PermissionDenied

    current_sources = Sound.objects.ordered_ids([element['id'] for element in sound.sources.all().values('id')])
    sources_string = ",".join(map(str, [source.id for source in current_sources]))
    if request.method == 'POST':
        form = RemixForm(sound, request.POST)
        if form.is_valid():
            form.save()
    else:
        form = RemixForm(sound, initial=dict(sources=sources_string))
    tvars = {
        'sound': sound,
        'form': form,
        'current_sources': current_sources
    }
    return render(request, 'sounds/sound_edit_sources.html', tvars)


def remixes(request, username, sound_id):
    sound = get_object_or_404(Sound, id=sound_id, moderation_state="OK", processing_state="OK")
    if sound.user.username.lower() != username.lower():
        raise Http404
    try:
        remix_group = sound.remix_group.all()[0]
    except:
        raise Http404
    return HttpResponseRedirect(reverse("remix-group", args=[remix_group.id]))


def remix_group(request, group_id):
    group = get_object_or_404(RemixGroup, id=group_id)
    data = group.protovis_data
    sounds = Sound.objects.ordered_ids(
        [element['id'] for element in group.sounds.all().order_by('created').values('id')])
    tvars = {
        'sounds': sounds,
        'last_sound': sounds[len(sounds)-1],
        'group_sound': sounds[0],
        'data': data,
    }
    return render(request, 'sounds/remixes.html', tvars)


def geotag(request, username, sound_id):
    sound = get_object_or_404(Sound, id=sound_id, moderation_state="OK", processing_state="OK")
    if sound.user.username.lower() != username.lower():
        raise Http404
    google_api_key = settings.GOOGLE_API_KEY
    return render(request, 'sounds/geotag.html', locals())


def similar(request, username, sound_id):
    sound = get_object_or_404(Sound,
                              id=sound_id,
                              moderation_state="OK",
                              processing_state="OK",
                              analysis_state="OK",
                              similarity_state="OK")
    if sound.user.username.lower() != username.lower():
        raise Http404

    similarity_results, count = get_similar_sounds(sound, request.GET.get('preset', None), int(settings.SOUNDS_PER_PAGE))
    logger.debug('Got similar_sounds for %s: %s' % (sound_id, similarity_results))
    similar_sounds = Sound.objects.ordered_ids([sound_id for sound_id, distance in similarity_results])
    return render(request, 'sounds/similar.html', locals())


def pack(request, username, pack_id):
    try:
        pack = Pack.objects.select_related().get(id=pack_id)
        if pack.user.username.lower() != username.lower():
            raise Http404
    except Pack.DoesNotExist:
        raise Http404

    if pack.is_deleted:
        return render(request, 'sounds/deleted_pack.html')

    qs = Sound.objects.only('id').filter(pack=pack, moderation_state="OK", processing_state="OK")
    paginate_data = paginate(request, qs, settings.SOUNDS_PER_PAGE)
    paginator = paginate_data['paginator']
    current_page = paginate_data['current_page']
    page = paginate_data['page']
    sound_ids = [sound_obj.id for sound_obj in page]
    pack_sounds = Sound.objects.ordered_ids(sound_ids)

    num_sounds_ok = len(qs)
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

    return render(request, 'sounds/pack.html', locals())


def packs_for_user(request, username):
    user = get_object_or_404(User, username__iexact=username)
    order = request.GET.get("order", "name")
    if order not in ["name", "-last_updated", "-created", "-num_sounds", "-num_downloads"]:
        order = "name"
    qs = Pack.objects.select_related().filter(user=user, num_sounds__gt=0).exclude(is_deleted=True).order_by(order)
    return render(request, 'sounds/packs.html', combine_dicts(paginate(request, qs, settings.PACKS_PER_PAGE), locals()))


def for_user(request, username):
    user = get_object_or_404(User, username__iexact=username)
    qs = Sound.public.only('id').filter(user=user)
    paginate_data = paginate(request, qs, settings.SOUNDS_PER_PAGE)
    paginator = paginate_data['paginator']
    current_page = paginate_data['current_page']
    page = paginate_data['page']
    sound_ids = [sound_obj.id for sound_obj in page]
    user_sounds = Sound.objects.ordered_ids(sound_ids)
    return render(request, 'sounds/for_user.html', locals())


@login_required
def delete(request, username, sound_id):
    sound = get_object_or_404(Sound, id=sound_id)
    if sound.user.username.lower() != username.lower():
        raise Http404

    if not (request.user.has_perm('sound.delete_sound') or sound.user == request.user):
        raise PermissionDenied

    error_message = None
    if request.method == "POST" :
        form = DeleteSoundForm(request.POST, sound_id=sound_id)
        if not form.is_valid():
            error_message = "Sorry, you waited too long, ... try again?"
            form = DeleteSoundForm(sound_id=sound_id)
        else:

            logger.debug("User %s requested to delete sound %s" % (request.user.username,sound_id))
            try:
                ticket = sound.ticket
                tc = TicketComment(sender=request.user,
                                   text="User %s deleted the sound" % request.user,
                                   ticket=ticket,
                                   moderator_only=False)
                tc.save()
            except Ticket.DoesNotExist:
                # No ticket assigned, not adding any message (should not happen)
                pass
            sound.delete()

            return HttpResponseRedirect(reverse("accounts-home"))
    else:
        form = DeleteSoundForm(sound_id=sound_id)

    tvars = {
            'error_message': error_message,
            'delete_form': form,
            'sound': sound
            }
    return render(request, 'sounds/delete.html', tvars)


def flag(request, username, sound_id):
    sound = get_object_or_404(Sound, id=sound_id, moderation_state="OK", processing_state="OK")
    if sound.user.username.lower() != username.lower():
        raise Http404

    user = None
    if request.user.is_authenticated:
        user = request.user

    if request.method == "POST":
        flag_form = FlagForm(request.POST)
        if flag_form.is_valid():
            flag = flag_form.save()
            flag.reporting_user = user
            flag.sound = sound
            flag.save()

            if user:
                user_email = user.email
            else:
                user_email = flag_form.cleaned_data["email"]

            from_email = settings.DEFAULT_FROM_EMAIL
            send_mail_template(u"[flag] flagged file", "sounds/email_flag.txt",
                               {"flag": flag}, from_email, reply_to=user_email)

            return redirect(sound)
    else:
        initial = {}
        if user:
            initial["email"] = user.email
        flag_form = FlagForm(initial=initial)

    tvars = {"sound": sound,
             "flag_form": flag_form}

    return render(request, 'sounds/sound_flag.html', tvars)


def sound_short_link(request, sound_id):
    sound = get_object_or_404(Sound, id=sound_id)
    return redirect('sound', username=sound.user.username,
            sound_id=sound.id)


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
    sound_obj = get_object_or_404(Sound, id=sound_id, user__username__iexact=username)

    # The following code is duplicated in sounds.tempaltetags.display_sound. This could be optimized.
    is_explicit = False
    if sound_obj is not None:
        is_explicit = sound_obj.is_explicit and \
                      (not request.user.is_authenticated or \
                       not request.user.profile.is_adult)
    tvars = {
        'sound_id': sound_id,
        'sound': sound_obj,
        'sound_tags': sound_obj.get_sound_tags(12),
        'sound_user': sound_obj.user.username,
        'license_name': sound_obj.license.name,
        'media_url': settings.MEDIA_URL,
        'request': request,
        'is_explicit': is_explicit
    }
    return render(request, 'sounds/display_sound.html', tvars)


def embed_iframe(request, sound_id, player_size):
    """
    This view returns an HTML player of `sound_id` which can be embeded in external sites.
    The player can take different "sizes" including:

        - 'mini': shows just a play button and a loop button. No background image.
          Eg: /embed/sound/iframe/1234/simple/mini/.
        - 'small': shows a play button, a loop button and the name of the user and sound.
          No background image. Eg: /embed/sound/iframe/1234/simple/small/.
        - 'medium': shows the waveform image with playing controls plus the sound name, username, license and some tags.
          Eg: /embed/sound/iframe/1234/simple/medium/.
        - 'medium_no_info': shows the waveform and with playing controls.
          Eg: /embed/sound/iframe/1234/simple/medium_no_info/.
        - 'large': shows the waveform image in large size with playing controls plus the sound name, username and license.
          Eg: /embed/sound/iframe/1234/simple/large/.
        - 'large_no_info': shows the waveform image in large size with playing controls.
          Eg: /embed/sound/iframe/1234/simple/large_no_info/.
        - 'full_size': like 'large' but taking the full width (used in twitter embeds).
          Eg: /embed/sound/iframe/1234/simple/full_size/.

    The sizes 'medium', 'medium_no_info', 'large', 'large_no_info' and 'full_size' can optionally show the spectrogram
    image instead of the waveform if being passed a request parameter 'spec=1' in the URL.
    Eg: /embed/sound/iframe/1234/simple/large/?spec=1.

    The sizes 'medium' and 'medium_no_info' can optionally show a button to toggle the background image between the
    waveform and the spectrogram by passing the request parameter 'td=1'. Bigger sizes always show that button.
    """
    if player_size not in ['mini', 'small', 'medium', 'large', 'large_no_info', 'medium_no_info', 'full_size']:
        raise Http404
    sound = get_object_or_404(Sound, id=sound_id, moderation_state='OK', processing_state='OK')
    tvars = {
        'sound': sound,
        'username_and_filename': '%s - %s' % (sound.user.username, sound.original_filename),
        'size': player_size,
        'use_spectrogram': request.GET.get('spec', None) == '1',
        'show_toggle_display_button': request.GET.get('td', None) == '1',
    }
    return render(request, 'sounds/sound_iframe.html', tvars)


def oembed(request):
    url = request.GET.get('url', '')
    view, args, kwargs = resolve(urlparse(url)[2])
    if not 'sound_id' in kwargs:
        raise Http404
    sound_id = kwargs['sound_id']
    sound = get_object_or_404(Sound, id=sound_id, moderation_state='OK', processing_state='OK')
    player_size = request.GET.get('size', 'medium')
    if player_size == 'large':
        sizes = settings.IFRAME_PLAYER_SIZE['large']
    if player_size == 'medium':
        sizes = settings.IFRAME_PLAYER_SIZE['medium']
    if player_size == 'small':
        sizes = settings.IFRAME_PLAYER_SIZE['small']
    tvars = {
        'sound': sound,
        'sizes': sizes,
        'player_size': player_size,
    }
    return render(request, 'sounds/sound_oembed.xml', tvars, content_type='text/xml')


def downloaders(request, username, sound_id):
    sound = get_object_or_404(Sound, id=sound_id)

    # Retrieve all users that downloaded a sound
    qs = Download.objects.filter(sound=sound_id)

    pagination = paginate(request, qs, 32, object_count=sound.num_downloads)
    page = pagination["page"]

    # Get all users+profiles for the user ids
    sounds = list(page)
    userids = [s.user_id for s in sounds]
    users = User.objects.filter(pk__in=userids).select_related("profile")
    user_map = {}
    for u in users:
        user_map[u.id] = u

    download_list = []
    for s in page:
        download_list.append({"created":s.created, "user": user_map[s.user_id]})
    download_list = sorted(download_list, key=itemgetter("created"), reverse=True)

    tvars = {"sound": sound,
             "username": username,
             "download_list": download_list}
    tvars.update(pagination)

    return render(request, 'sounds/downloaders.html', tvars)


def pack_downloaders(request, username, pack_id):
    pack = get_object_or_404(Pack, id = pack_id)

    # Retrieve all users that downloaded a sound
    qs = Download.objects.filter(pack=pack_id)
    return render(request, 'sounds/pack_downloaders.html', combine_dicts(paginate(request, qs, 32, object_count=pack.num_downloads), locals()))
