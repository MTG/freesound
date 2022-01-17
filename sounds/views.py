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

import datetime
import json
import logging
import time
from collections import defaultdict
from django.views.decorators.clickjacking import xframe_options_exempt
from operator import itemgetter

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.db.models.functions import Greatest
from django.http import HttpResponse
from django.http import HttpResponseRedirect, Http404, \
    HttpResponsePermanentRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template import loader
from django.urls import reverse, resolve
from django.utils.six.moves.urllib.parse import urlparse
from ratelimit.decorators import ratelimit

from comments.forms import CommentForm
from comments.models import Comment
from donations.models import DonationsModalSettings, Donation
from follow import follow_utils
from forum.models import Thread
from forum.views import get_hot_threads
from geotags.models import GeoTag
from sounds.forms import DeleteSoundForm, FlagForm, SoundDescriptionForm, GeotaggingForm, NewLicenseForm, PackEditForm, \
    RemixForm, PackForm
from sounds.models import PackDownload, PackDownloadSound
from sounds.models import Sound, Pack, Download, RemixGroup, DeletedSound, SoundOfTheDay
from tickets import TICKET_STATUS_CLOSED
from tickets.models import Ticket, TicketComment
from utils.downloads import download_sounds, should_suggest_donation
from utils.encryption import encrypt, decrypt
from utils.frontend_handling import render, using_beastwhoosh, redirect_if_beastwhoosh
from utils.mail import send_mail_template, send_mail_template_to_support
from utils.nginxsendfile import sendfile, prepare_sendfile_arguments_for_sound_download
from utils.pagination import paginate
from utils.ratelimit import key_for_ratelimiting, rate_per_ip
from utils.search.search_general import get_random_sound_from_solr
from utils.similarity_utilities import get_similar_sounds
from utils.text import remove_control_chars
from utils.username import redirect_if_old_username_or_404

web_logger = logging.getLogger('web')


def get_n_weeks_back_datetime(n_weeks):
    """
    Returns a datetime object set to a time `n_weeks` back from now.
    If DEBUG=True, it is likely that the contents of the development databse have not been updated and no
    activity will be registered for the last `n_weeks`. To compensate for that, when in DEBUG mode the returned
    date is calculated with respect to the date of the most recent download stored in database. In this way it is
    more likely that the selected time range will include activity in database.
    """
    now = datetime.datetime.now()
    if settings.DEBUG:
        now = Download.objects.first().created
    return now - datetime.timedelta(weeks=n_weeks)


def get_sound_of_the_day_id():
    """
    Returns random id of sound (int)
    """
    cache_key = settings.RANDOM_SOUND_OF_THE_DAY_CACHE_KEY
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


@redirect_if_beastwhoosh('sounds-search', query_string='s=created+desc&g=1')
def sounds(request):
    latest_sounds = Sound.objects.latest_additions(num_sounds=5, period_days=2)    
    latest_packs = Pack.objects.select_related().filter(num_sounds__gt=0).exclude(is_deleted=True).order_by("-last_updated")[0:20]
    last_week = get_n_weeks_back_datetime(n_weeks=1)
    popular_sounds = Sound.public.select_related('license', 'user') \
                                 .annotate(greatest_date=Greatest('created', 'moderation_date')) \
                                 .filter(greatest_date__gte=last_week).order_by("-num_downloads")[0:5]
    popular_packs = Pack.objects.select_related('user').filter(created__gte=last_week).exclude(is_deleted=True).order_by("-num_downloads")[0:5]
    random_sound_id = get_sound_of_the_day_id()
    if random_sound_id:
        try:
            random_sound = Sound.objects.bulk_query_id([random_sound_id])[0]
        except IndexError:
            # Clear existing cache for random sound of the day as it contains invalid sound id
            cache.delete(settings.RANDOM_SOUND_OF_THE_DAY_CACHE_KEY)
            random_sound = None
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


@redirect_if_beastwhoosh('sounds-search', query_string='s=created+desc&g=1&only_p=1')
def packs(request):
    order = request.GET.get("order", "name")
    if order not in ["name", "-last_updated", "-created", "-num_sounds", "-num_downloads"]:
        order = "name"
    qs = Pack.objects.select_related() \
                     .filter(num_sounds__gt=0) \
                     .exclude(is_deleted=True) \
                     .order_by(order)
    tvars = {'order': order}
    tvars.update(paginate(request, qs, settings.PACKS_PER_PAGE))
    return render(request, 'sounds/browse_packs.html', tvars)


def front_page(request):
    rss_cache = cache.get("rss_cache_bw" if using_beastwhoosh(request) else "rss_cache", None)
    trending_sound_ids = cache.get("trending_sound_ids", None)
    trending_new_sound_ids = cache.get("trending_new_sound_ids", None)
    trending_new_pack_ids = cache.get("trending_new_pack_ids", None)
    total_num_sounds = cache.get("total_num_sounds", 0)
    popular_searches = cache.get("popular_searches", None)
    top_donor_user_id = cache.get("top_donor_user_id", None)
    top_donor_donation_amount = cache.get("top_donor_donation_amount", None)
    if popular_searches is not None:
        popular_searches = [(query_terms, '{0}?q={1}'.format(reverse('sounds-search'), query_terms))
                            for query_terms in popular_searches]

    current_forum_threads = get_hot_threads(n=10)

    num_latest_sounds = 5 if not using_beastwhoosh(request) else 9
    latest_sounds = Sound.objects.latest_additions(num_sounds=num_latest_sounds, period_days=2)
    random_sound_id = get_sound_of_the_day_id()
    if random_sound_id:
        try:
            random_sound = Sound.objects.bulk_query_id([random_sound_id])[0]
        except IndexError:
            # Clear existing cache for random sound of the day as it contains invalid sound id
            cache.delete(settings.RANDOM_SOUND_OF_THE_DAY_CACHE_KEY)
            random_sound = None
    else:
        random_sound = None

    tvars = {
        'rss_cache': rss_cache,
        'popular_searches': popular_searches,
        'trending_sound_ids': trending_sound_ids,
        'trending_new_sound_ids': trending_new_sound_ids,
        'trending_new_pack_ids': trending_new_pack_ids,
        'current_forum_threads': current_forum_threads,
        'latest_sounds': latest_sounds,
        'random_sound': random_sound,
        'top_donor_user_id': top_donor_user_id,
        'top_donor_donation_amount': top_donor_donation_amount,
        'total_num_sounds': total_num_sounds,
        'is_authenticated': request.user.is_authenticated(),
        'donation_amount_request_param': settings.DONATION_AMOUNT_REQUEST_PARAM,
        'enable_query_suggestions': settings.ENABLE_QUERY_SUGGESTIONS,  # Used for beast whoosh only
        'query_suggestions_url': reverse('query-suggestions'),  # Used for beast whoosh only
        'enable_popular_searches': settings.ENABLE_POPULAR_SEARCHES_IN_FRONTPAGE,  # Used for beast whoosh only
    }
    return render(request, 'front.html', tvars)


@redirect_if_old_username_or_404
def sound(request, username, sound_id):
    try:
        sound = Sound.objects.prefetch_related("tags__tag")\
            .select_related("license", "user", "user__profile", "pack")\
            .get(id=sound_id, user__username=username)

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
            return render(request, 'sounds/sound_deleted.html')
        else:
            raise Http404

    if request.method == "POST":
        form = CommentForm(request, request.POST)
        if request.user.is_authenticated:
            if request.user.profile.is_blocked_for_spam_reports():
                messages.add_message(request, messages.INFO, "You're not allowed to post the comment because your "
                                                             "account has been temporaly blocked after multiple spam "
                                                             "reports")
            else:
                if form.is_valid():
                    comment_text = form.cleaned_data["comment"]
                    sound.add_comment(request.user, comment_text)
                    sound.invalidate_template_caches()
                    send_mail_template(settings.EMAIL_SUBJECT_NEW_COMMENT, 'sounds/email_new_comment.txt',
                                       {'sound': sound, 'user': request.user, 'comment': comment_text},
                                       user_to=sound.user, email_type_preference_check="new_comment")

                    return HttpResponseRedirect(sound.get_absolute_url())
    else:
        form = CommentForm(request)

    qs = Comment.objects.select_related("user", "user__profile")\
        .filter(sound_id=sound_id)
    display_random_link = request.GET.get('random_browsing', False)
    is_following = request.user.is_authenticated() and follow_utils.is_user_following_user(request.user, sound.user)
    is_explicit = sound.is_explicit and (not request.user.is_authenticated or not request.user.profile.is_adult)

    tvars = {
        'sound': sound,
        'username': username,
        'form': form,
        'display_random_link': display_random_link,
        'is_following': is_following,
        'is_explicit': is_explicit,  # if the sound should be shown blurred, already checks for adult profile
        'sizes': settings.IFRAME_PLAYER_SIZE,
        'min_num_ratings': settings.MIN_NUMBER_RATINGS
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
    should_show_modal = False
    bw_response = None

    def modal_shown_timestamps_cache_key(user):
        return 'modal_shown_timestamps_donations_shown_%i' % user.id

    if DonationsModalSettings.get_donation_modal_settings().enabled:
        # Get timestamps of last times modal was shown from cache
        modal_shown_timestamps = cache.get(modal_shown_timestamps_cache_key(request.user), [])

        # Iterate over timestamps, keep only the ones in last 24 hours and do the counting
        modal_shown_timestamps = [item for item in modal_shown_timestamps if item > (time.time() - 24 * 3600)]

        if should_suggest_donation(request.user, len(modal_shown_timestamps)):
            web_logger.info('Showing after download donate modal (%s)' % json.dumps({'user_id': request.user.id}))
            modal_shown_timestamps.append(time.time())
            cache.set(modal_shown_timestamps_cache_key(request.user), modal_shown_timestamps,
                      60 * 60 * 24)  # 24 lifetime cache
            should_show_modal = True

    if should_show_modal:
        if using_beastwhoosh(request):
            return render(request, 'donations/modal_after_download_donation_request.html',
                          {'donation_amount_request_param': settings.DONATION_AMOUNT_REQUEST_PARAM})
        else:
            template = loader.get_template('sounds/after_download_modal_donation.html')
            response_content = template.render({'sound_name': sound_name})
            return JsonResponse({'content': response_content})
    else:
        if using_beastwhoosh(request):
            return HttpResponse()
        else:
            return JsonResponse({'content': None})


@redirect_if_old_username_or_404
@transaction.atomic()
def sound_download(request, username, sound_id):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('%s?next=%s' % (reverse("login"),
                                                    reverse("sound", args=[username, sound_id])))
    sound = get_object_or_404(Sound, id=sound_id, moderation_state="OK", processing_state="OK")
    if sound.user.username.lower() != username.lower():
        raise Http404

    if 'HTTP_RANGE' not in request.META:
        """
        Download managers and some browsers use the range header to download files in multiple parts. We have observed 
        that all clients first make a GET with no range header (to get the file length) and then make multiple other 
        requests. We ignore all requests that have range header because we assume that a first query has already been 
        made. We additionally guard against users clicking on download multiple times by storing a sentinel in the 
        cache for 5 minutes.
        """
        cache_key = 'sdwn_%s_%d' % (sound_id, request.user.id)
        if cache.get(cache_key, None) is None:
            Download.objects.create(user=request.user, sound=sound, license_id=sound.license_id)
            sound.invalidate_template_caches()
            cache.set(cache_key, True, 60 * 5)  # Don't save downloads for the same user/sound in 5 minutes

    return sendfile(*prepare_sendfile_arguments_for_sound_download(sound))


@redirect_if_old_username_or_404
@transaction.atomic()
def pack_download(request, username, pack_id):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('%s?next=%s' % (reverse("login"),
                                                    reverse("pack", args=[username, pack_id])))
    pack = get_object_or_404(Pack, id=pack_id)
    if pack.user.username.lower() != username.lower():
        raise Http404

    if 'HTTP_RANGE' not in request.META:
        """
        Download managers and some browsers use the range header to download files in multiple parts. We have observed 
        that all clients first make a GET with no range header (to get the file length) and then make multiple other 
        requests. We ignore all requests that have range header because we assume that a first query has already been 
        made. We additionally guard against users clicking on download multiple times by storing a sentinel in the 
        cache for 5 minutes.
        """
        cache_key = 'pdwn_%s_%d' % (pack_id, request.user.id)
        if cache.get(cache_key, None) is None:
            pd = PackDownload.objects.create(user=request.user, pack=pack)
            pds = []
            for sound in pack.sounds.all():
                pds.append(PackDownloadSound(sound=sound, license_id=sound.license_id, pack_download=pd))
            PackDownloadSound.objects.bulk_create(pds)
            cache.set(cache_key, True, 60 * 5)  # Don't save downloads for the same user/pack in the next 5 minutes
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

    if not (request.user.is_superuser or sound.user == request.user):
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
                    sound.geotag.should_update_information = True
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
    if request.method == 'POST' and license_form.is_valid():
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
@transaction.atomic()
def pack_edit(request, username, pack_id):
    pack = get_object_or_404(Pack, id=pack_id)
    if pack.user.username.lower() != username.lower():
        raise Http404
    pack_sounds = ",".join([str(s.id) for s in pack.sounds.all()])

    if not (request.user.has_perm('pack.can_change') or pack.user == request.user):
        raise PermissionDenied

    current_sounds = list()
    if request.method == "POST":
        form = PackEditForm(request.POST, instance=pack)
        if form.is_valid():
            form.save()
            pack.sounds.all().update(is_index_dirty=True)
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
@transaction.atomic()
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
            web_logger.info("User %s requested to delete pack %s" % (request.user.username, pack_id))
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
@transaction.atomic()
def sound_edit_sources(request, username, sound_id):
    sound = get_object_or_404(Sound, id=sound_id)
    if sound.user.username.lower() != username.lower():
        raise Http404

    if not (request.user.is_superuser or sound.user == request.user):
        raise PermissionDenied

    current_sources = Sound.objects.ordered_ids([element['id'] for element in sound.sources.all().values('id')])
    sources_string = ",".join(map(str, [source.id for source in current_sources]))
    if request.method == 'POST':
        form = RemixForm(sound, request.POST)
        if form.is_valid():
            form.save()
            sound.invalidate_template_caches()
    else:
        form = RemixForm(sound, initial=dict(sources=sources_string))
    tvars = {
        'sound': sound,
        'form': form,
        'current_sources': current_sources
    }
    return render(request, 'sounds/sound_edit_sources.html', tvars)


@redirect_if_old_username_or_404
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


@redirect_if_old_username_or_404
@ratelimit(key=key_for_ratelimiting, rate=rate_per_ip, group=settings.RATELIMIT_SIMILARITY_GROUP, block=True)
def similar(request, username, sound_id):
    if using_beastwhoosh(request) and not request.GET.get('ajax'):
        return HttpResponseRedirect(reverse('sound', args=[username, sound_id]) + '?similar=1')

    sound = get_object_or_404(Sound,
                              id=sound_id,
                              moderation_state="OK",
                              processing_state="OK",
                              analysis_state="OK",
                              similarity_state="OK")
    if sound.user.username.lower() != username.lower():
        raise Http404

    similarity_results, count = get_similar_sounds(sound, request.GET.get('preset', None), int(settings.SOUNDS_PER_PAGE))
    similar_sounds = Sound.objects.ordered_ids([sound_id for sound_id, distance in similarity_results])

    tvars = {'similar_sounds': similar_sounds}
    if using_beastwhoosh(request):
        # In BW similar sounds are displayed in a modal
        return render(request, 'sounds/modal_similar_sounds.html', tvars)
    else:
        return render(request, 'sounds/similar.html', tvars)


@redirect_if_old_username_or_404
@transaction.atomic()
def pack(request, username, pack_id):
    try:
        pack = Pack.objects.select_related().get(id=pack_id)
        if pack.user.username.lower() != username.lower():
            raise Http404
    except Pack.DoesNotExist:
        raise Http404

    if pack.is_deleted:
        return render(request, 'sounds/pack_deleted.html')

    qs = Sound.public.only('id').filter(pack=pack).order_by('-created')
    paginator = paginate(request, qs, settings.SOUNDS_PER_PAGE if not using_beastwhoosh(request) else 12)
    sound_ids = [sound_obj.id for sound_obj in paginator['page']]
    pack_sounds = Sound.objects.ordered_ids(sound_ids)

    num_sounds_ok = paginator['paginator'].count
    if num_sounds_ok < pack.num_sounds:
        messages.add_message(request, messages.INFO,
                             'Some sounds of this pack might <b>not have been moderated or processed</b> yet.')

    is_following = None
    geotags_in_pack_serialized = []
    if using_beastwhoosh(request):
        is_following = request.user.is_authenticated() and follow_utils.is_user_following_user(request.user, pack.user)
        if pack.has_geotags and settings.MAPBOX_USE_STATIC_MAPS_BEFORE_LOADING:
            for sound in Sound.public.select_related('geotag').filter(pack__id=pack_id).exclude(geotag=None):
                geotags_in_pack_serialized.append({'lon': sound.geotag.lon, 'lat': sound.geotag.lat})
            geotags_in_pack_serialized = json.dumps(geotags_in_pack_serialized)

    tvars = {
        'pack': pack,
        'num_sounds_ok': num_sounds_ok,
        'pack_sounds': pack_sounds,
        'min_num_ratings': settings.MIN_NUMBER_RATINGS,  # BW only
        'is_following': is_following,
        'geotags_in_pack_serialized': geotags_in_pack_serialized  # BW only
    }
    if not using_beastwhoosh(request):
        tvars.update(paginator)

    return render(request, 'sounds/pack.html', tvars)


@redirect_if_old_username_or_404
def packs_for_user(request, username):
    if using_beastwhoosh(request):
        return HttpResponseRedirect('{0}?f=username:%22{1}%22&s=created+desc&g=1&only_p=1'.format(reverse('sounds-search'), username))

    user = request.parameter_user
    order = request.GET.get("order", "name")
    if order not in ["name", "-last_updated", "-created", "-num_sounds", "-num_downloads"]:
        order = "name"
    qs = Pack.objects.select_related().filter(user=user, num_sounds__gt=0).exclude(is_deleted=True).order_by(order)
    paginator = paginate(request, qs, settings.PACKS_PER_PAGE)

    tvars = {'user': user,
             'order': order}
    tvars.update(paginator)
    return render(request, 'sounds/packs.html', tvars)


@redirect_if_old_username_or_404
def for_user(request, username):
    if using_beastwhoosh(request):
        return HttpResponseRedirect('{0}?f=username:%22{1}%22&s=created+desc&g=1'.format(reverse('sounds-search'), username))

    sound_user = request.parameter_user
    paginator = paginate(request, Sound.public.only('id').filter(user=sound_user), settings.SOUNDS_PER_PAGE)
    sound_ids = [sound_obj.id for sound_obj in paginator['page']]
    user_sounds = Sound.objects.ordered_ids(sound_ids)

    tvars = {'sound_user': sound_user,
             'user_sounds': user_sounds}
    tvars.update(paginator)
    return render(request, 'sounds/for_user.html', tvars)


@login_required
@transaction.atomic()
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

            web_logger.info("User %s requested to delete sound %s" % (request.user.username,sound_id))
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


@redirect_if_old_username_or_404
@transaction.atomic()
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
                user_email = user.profile.get_email_for_delivery()
            else:
                user_email = flag_form.cleaned_data["email"]

            send_mail_template_to_support(settings.EMAIL_SUBJECT_SOUND_FLAG, "sounds/email_flag.txt", {"flag": flag},
                                          extra_subject="%s - %s" % (sound.user.username, sound.original_filename),
                                          reply_to=user_email)
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
    return redirect('sound', username=sound.user.username, sound_id=sound.id)


def pack_short_link(request, pack_id):
    pack = get_object_or_404(Pack, id=pack_id)
    return redirect('pack', username=pack.user.username, pack_id=pack.id)


def __redirect_old_link(request, cls, url_name):
    obj_id = request.GET.get('id', False)
    if obj_id:
        try:
            obj_id = int(obj_id)
            obj = get_object_or_404(cls, id=obj_id)
            return HttpResponsePermanentRedirect(reverse(url_name, args=[obj.user.username, obj_id]))
        except ValueError:
            raise Http404
    else:
        raise Http404


def old_sound_link_redirect(request):
    return __redirect_old_link(request, Sound, "sound")


def old_pack_link_redirect(request):
    return __redirect_old_link(request, Pack, "pack")


@redirect_if_old_username_or_404
def display_sound_wrapper(request, username, sound_id):
    sound_obj = get_object_or_404(Sound, id=sound_id)
    if sound_obj.user.username.lower() != username.lower():
        raise Http404

    # The following code is duplicated in sounds.templatetags.display_sound. This could be optimized.
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
        'is_explicit': is_explicit,
        'is_authenticated': request.user.is_authenticated()  # cache computation is weird with CallableBool
    }
    return render(request, 'sounds/display_sound.html', tvars)


@xframe_options_exempt
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
        download_list.append({"created": s.created, "user": user_map[s.user_id]})
    download_list = sorted(download_list, key=itemgetter("created"), reverse=True)

    tvars = {"sound": sound,
             "username": username,
             "download_list": download_list}
    tvars.update(pagination)

    return render(request, 'sounds/downloaders.html', tvars)


def pack_downloaders(request, username, pack_id):
    pack = get_object_or_404(Pack, id=pack_id)

    # Retrieve all users that downloaded a sound
    qs = PackDownload.objects.filter(pack_id=pack_id).select_related("user", "user__profile")
    paginator = paginate(request, qs, 32, object_count=pack.num_downloads)

    tvars = {'username': username,
             'pack': pack}
    tvars.update(paginator)
    return render(request, 'sounds/pack_downloaders.html', tvars)
