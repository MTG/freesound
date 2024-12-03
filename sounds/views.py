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
import math
import os
import time
import uuid
from builtins import map
from builtins import str
from operator import itemgetter
from urllib.parse import urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.core.cache import cache, caches
from django.core.exceptions import PermissionDenied
from django.core.signing import BadSignature, SignatureExpired
from django.db import transaction
from django.db.models.functions import Greatest
from django.http import HttpResponse
from django.http import HttpResponseRedirect, Http404, \
    HttpResponsePermanentRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader
from django.urls import reverse, resolve
from django.views.decorators.clickjacking import xframe_options_exempt
from ratelimit.decorators import ratelimit

from accounts.models import Profile
from comments.forms import CommentForm
from comments.models import Comment
from donations.models import DonationsModalSettings
from follow import follow_utils
from forum.views import get_hot_threads
from geotags.models import GeoTag
from sounds.forms import FlagForm,PackEditForm, SoundEditAndDescribeForm
from sounds.models import PackDownload, PackDownloadSound
from sounds.models import Sound, Pack, Download, RemixGroup, DeletedSound, SoundOfTheDay
from tickets import TICKET_STATUS_CLOSED
from tickets.models import Ticket, TicketComment
from utils.cache import invalidate_user_template_caches
from utils.downloads import download_sounds, should_suggest_donation
from utils.mail import send_mail_template, send_mail_template_to_support
from utils.nginxsendfile import sendfile, prepare_sendfile_arguments_for_sound_download
from utils.pagination import paginate
from utils.ratelimit import key_for_ratelimiting, rate_per_ip
from utils.search import get_search_engine, SearchEngineException
from utils.search.search_sounds import get_random_sound_id_from_search_engine, perform_search_engine_query
from utils.similarity_utilities import get_similar_sounds
from utils.sound_upload import create_sound, NoAudioException, AlreadyExistsException, CantMoveException, \
    clean_processing_before_describe_files, get_processing_before_describe_sound_base_url, \
    get_duration_from_processing_before_describe_files, \
    get_samplerate_from_processing_before_describe_files
from utils.text import remove_control_chars
from utils.username import redirect_if_old_username_or_404

web_logger = logging.getLogger('web')
sounds_logger = logging.getLogger('sounds')
upload_logger = logging.getLogger('file_upload')
cache_cdn_map = caches["cdn_map"]


def get_n_weeks_back_datetime(n_weeks):
    """
    Returns a datetime object set to a time `n_weeks` back from now.
    If DEBUG=True, it is likely that the contents of the development databse have not been updated and no
    activity will be registered for the last `n_weeks`. To compensate for that, when in DEBUG mode the returned
    date is calculated with respect to the date of the most recent sound stored in database. In this way it is
    more likely that the selected time range will include activity in database.
    """
    now = datetime.datetime.now()
    if settings.DEBUG:
        now = Sound.objects.last().created
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


def sounds(request):
    return HttpResponseRedirect(reverse('sounds-search') + '?s=Date+added+(newest+first)&g=1')


@ratelimit(key=key_for_ratelimiting, rate=rate_per_ip, group=settings.RATELIMIT_SEARCH_GROUP, block=True)
def random(request):
    random_sound_id = get_random_sound_id_from_search_engine()
    sound_obj = None
    if random_sound_id:
        try:
            # There is a small edge case where a sound may have been marked
            # as explicit and is selected here before the index is updated,
            # but we expect this to happen rarely enough that it's not a problem
            sound_obj = Sound.objects.get(id=random_sound_id)
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
    return HttpResponseRedirect(reverse('sounds-search') + '?s=Date+added+(newest+first)&g=1&dp=1')


def front_page(request):
    rss_cache = cache.get("rss_cache", None)
    trending_sound_ids = cache.get("trending_sound_ids", None)
    trending_new_sound_ids = cache.get("trending_new_sound_ids", None)
    top_rated_new_sound_ids = cache.get("top_rated_new_sound_ids", None)
    trending_new_pack_ids = cache.get("trending_new_pack_ids", None)
    recent_random_sound_ids = cache.get("recent_random_sound_ids", None)
    total_num_sounds = cache.get("total_num_sounds", 0)
    popular_searches = cache.get("popular_searches", None)
    top_donor_user_id = cache.get("top_donor_user_id", None)
    top_donor_donation_amount = cache.get("top_donor_donation_amount", None)
    if popular_searches is not None:
        popular_searches = [(query_terms, f"{reverse('sounds-search')}?q={query_terms}")
                            for query_terms in popular_searches]

    current_forum_threads = get_hot_threads(n=10)

    num_latest_sounds = 12
    latest_sounds = Sound.objects.latest_additions(num_sounds=num_latest_sounds, period_days=2)
    random_sound_id = get_sound_of_the_day_id()
    if random_sound_id:
        try:
            random_sound = lambda: Sound.objects.bulk_query_id([random_sound_id])[0]
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
        'top_rated_new_sound_ids': top_rated_new_sound_ids,
        'trending_new_pack_ids': trending_new_pack_ids,
        'recent_random_sound_ids': recent_random_sound_ids,
        'current_forum_threads': current_forum_threads,
        'latest_sounds': latest_sounds,
        'random_sound': random_sound,
        'top_donor_user_id': top_donor_user_id,
        'top_donor_donation_amount': top_donor_donation_amount,
        'total_num_sounds': total_num_sounds,
        'is_authenticated': request.user.is_authenticated,
        'donation_amount_request_param': settings.DONATION_AMOUNT_REQUEST_PARAM,
        'enable_query_suggestions': settings.ENABLE_QUERY_SUGGESTIONS,
        'query_suggestions_url': reverse('query-suggestions'),
        'enable_popular_searches': settings.ENABLE_POPULAR_SEARCHES_IN_FRONTPAGE,
        'announcement_cache': cache.get(settings.ANNOUNCEMENT_CACHE_KEY, None),
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
                    if request.user != sound.user:
                        send_mail_template(
                            settings.EMAIL_SUBJECT_NEW_COMMENT, 'emails/email_new_comment.txt',
                            {'sound': sound, 'user': request.user, 'comment': comment_text},
                            user_to=sound.user, email_type_preference_check="new_comment")

                    return HttpResponseRedirect(sound.get_absolute_url())
    else:
        form = CommentForm(request)

    qs = Comment.objects.select_related("user", "user__profile")\
        .filter(sound_id=sound_id)
    display_random_link = request.GET.get('random_browsing', False)
    is_following = request.user.is_authenticated and follow_utils.is_user_following_user(request.user, sound.user)
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
            web_logger.info(f"Showing after download donate modal ({json.dumps({'user_id': request.user.id})})")
            modal_shown_timestamps.append(time.time())
            cache.set(modal_shown_timestamps_cache_key(request.user), modal_shown_timestamps,
                      60 * 60 * 24)  # 24 lifetime cache
            should_show_modal = True

    if should_show_modal:
        return render(request, 'donations/modal_after_download_donation_request.html',
                        {'donation_amount_request_param': settings.DONATION_AMOUNT_REQUEST_PARAM})
    else:
        return HttpResponse()


@redirect_if_old_username_or_404
@transaction.atomic()
def sound_download(request, username, sound_id):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('{}?next={}'.format(reverse("login"),
                                                    reverse("sound", args=[username, sound_id])))
    sound = get_object_or_404(Sound, id=sound_id, moderation_state="OK", processing_state="OK")
    if sound.user.username.lower() != username.lower():
        raise Http404

    if 'range' not in request.headers:
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

    if settings.USE_CDN_FOR_DOWNLOADS:
        cdn_filename = cache_cdn_map.get(str(sound_id), None)
        if cdn_filename is not None:
            # If USE_CDN_FOR_DOWNLOADS option is on and we find an URL for that sound in the CDN, then we redirect to that one
            cdn_url = settings.CDN_DOWNLOADS_TEMPLATE_URL.format(int(sound_id) // 1000, cdn_filename, sound.friendly_filename())
            return HttpResponseRedirect(cdn_url)

    return sendfile(*prepare_sendfile_arguments_for_sound_download(sound))


@redirect_if_old_username_or_404
@transaction.atomic()
def pack_download(request, username, pack_id):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('{}?next={}'.format(reverse("login"),
                                                    reverse("pack", args=[username, pack_id])))
    pack = get_object_or_404(Pack, id=pack_id)
    if pack.user.username.lower() != username.lower():
        raise Http404

    if 'range' not in request.headers:
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
    licenses_content = pack.get_attribution()
    sound_list = pack.sounds.filter(processing_state="OK", moderation_state="OK").select_related('user', 'license')
    print(licenses_content)
    return download_sounds(licenses_url, licenses_content, sound_list)


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

    session_key_prefix = request.GET.get('session', str(uuid.uuid4())[0:8])  # Get existing session key if we are already in an edit session or create a new one
    request.session[f'{session_key_prefix}-edit_sounds'] = [sound]  # Add the list of sounds to edit in the session object
    request.session[f'{session_key_prefix}-len_original_edit_sounds'] = 1
    return edit_and_describe_sounds_helper(request, session_key_prefix=session_key_prefix)


def clear_session_edit_data(request, session_key_prefix=''):
    # Clear pre-existing edit/describe sound related data in the session
    for key in ['edit_sounds', 'len_original_edit_sounds']:
        request.session.pop(f'{session_key_prefix}-{key}', None)


def clear_session_describe_data(request, session_key_prefix=''):
    # Clear pre-existing edit/describe sound related data in the session
    for key in ['describe_sounds','describe_license', 'describe_pack', 'len_original_describe_sounds']:
        request.session.pop(f'{session_key_prefix}-{key}', None)


def edit_and_describe_sounds_helper(request, describing=False, session_key_prefix=''):

    def update_sound_tickets(sound, text):
        tickets = Ticket.objects.filter(sound_id=sound.id).exclude(status=TICKET_STATUS_CLOSED)
        for ticket in tickets:
            tc = TicketComment(sender=request.user,
                               ticket=ticket,
                               moderator_only=False,
                               text=text)
            tc.save()
            ticket.send_notification_emails(ticket.NOTIFICATION_UPDATED,
                                            ticket.MODERATOR_ONLY)

    def create_sounds(request, forms):
        # Create actual Sound objects, trigger processing of sounds and of affected packs
        sounds_to_process = []
        dirty_packs = []
        for form in forms:
            file_full_path=form.file_full_path
            if not file_full_path.endswith(form.audio_filename_from_form):
                continue  # Double check that we are not writing to the wrong file
            sound_fields = {
                'name': form.cleaned_data['name'],
                'dest_path': file_full_path,
                'license': form.cleaned_data['license'],
                'description': form.cleaned_data.get('description', ''),
                'tags': form.cleaned_data.get('tags', ''),
                'is_explicit': form.cleaned_data['is_explicit'],
            }

            pack = form.cleaned_data.get('pack', False)
            new_pack = form.cleaned_data.get('new_pack', False)
            if not pack and new_pack:
                sound_fields['pack'] = new_pack
            elif pack:
                sound_fields['pack'] = pack

            if not form.cleaned_data.get('remove_geotag') and form.cleaned_data.get('lat'):  # if 'lat' is in data, we assume other fields are too
                geotag = '%s,%s,%d' % (form.cleaned_data.get('lat'), form.cleaned_data.get('lon'), form.cleaned_data.get('zoom'))
                sound_fields['geotag'] = geotag
            
            try:
                user = request.user
                sound = create_sound(user, sound_fields, process=False)
                sound_sources = form.cleaned_data['sources']
                if sound_sources:
                    sound.set_sources(sound_sources)
                sounds_to_process.append(sound)
                if user.profile.is_whitelisted:
                    messages.add_message(request, messages.INFO,
                        'File <a href="{}">{}</a> has been described and has been added to freesound.'\
                            .format(sound.get_absolute_url(), sound.original_filename))
                else:
                    messages.add_message(request, messages.INFO,
                        'File <a href="{}">{}</a> has been described and is now awaiting processing and moderation.'\
                            .format(sound.get_absolute_url(), sound.original_filename))
                    invalidate_user_template_caches(request.user.id)
                    for moderator in Group.objects.get(name='moderators').user_set.all():
                        invalidate_user_template_caches(moderator.id)
                clean_processing_before_describe_files(file_full_path)

            except NoAudioException:
                # If for some reason audio file does not exist, skip creating this sound
                messages.add_message(request, messages.ERROR,
                                     f"Something went wrong with accessing the file {form.cleaned_data['name']}.")
            except AlreadyExistsException as e:
                messages.add_message(request, messages.WARNING, str(e))
            except CantMoveException as e:
                upload_logger.info(str(e))

        # Trigger processing of sounds and of affected packs
        try:
            for s in sounds_to_process:
                s.process_and_analyze(countdown=10)
        except Exception as e:
            sounds_logger.info(f'Sound with id {s.id} could not be sent to processing. ({str(e)})')
        for p in dirty_packs:
            p.process()

    def update_edited_sound(sound, data):
        sound.is_explicit = data["is_explicit"]
        sound.set_tags(data["tags"])
        sound.description = remove_control_chars(data["description"])
        sound.original_filename = data["name"]
        
        new_license = data["license"]
        if new_license != sound.license:
            sound.set_license(new_license)
        
        packs_to_process = []
        if data['new_pack']:
            pack, _ = Pack.objects.get_or_create(user=sound.user, name=data['new_pack'])
            if sound.pack:
                packs_to_process.append(sound.pack)  # Append previous sound pack if exists
            sound.pack = pack
            packs_to_process.append(pack)
        else:
            new_pack = data["pack"]
            old_pack = sound.pack
            if new_pack != old_pack:
                sound.pack = new_pack
                if new_pack:
                    packs_to_process.append(new_pack)
                if old_pack:
                    packs_to_process.append(old_pack)

        if data["remove_geotag"]:
            if sound.geotag:
                sound.geotag.delete()
                sound.geotag = None
        else:
            if data["lat"] and data["lon"] and data["zoom"]:
                if sound.geotag:
                    sound.geotag.lat = data["lat"]
                    sound.geotag.lon = data["lon"]
                    sound.geotag.zoom = data["zoom"]
                    sound.geotag.should_update_information = True
                    sound.geotag.save()
                else:
                    sound.geotag = GeoTag.objects.create(
                        lat=data["lat"], lon=data["lon"], zoom=data["zoom"], user=request.user)

        sound_sources = data["sources"]
        if sound_sources != sound.get_sound_sources_as_set():
            sound.set_sources(sound_sources)
        
        sound.mark_index_dirty()  # Sound is saved here
        sound.invalidate_template_caches()
        update_sound_tickets(sound, f'{request.user.username} updated one or more fields of the sound description.')
        messages.add_message(request, messages.INFO,
            f'Sound <a href="{sound.get_absolute_url()}">{sound.original_filename}</a> successfully edited!')

        for packs_to_process in packs_to_process:
            packs_to_process.process()

    files = request.session.get(f'{session_key_prefix}-describe_sounds', None)  # List of File objects of sounds to describe
    sounds = request.session.get(f'{session_key_prefix}-edit_sounds', None)  # List of Sound objects to edit
    if (describing and files is None) or (not describing and sounds is None):
        # Expecting either a list of sounds or audio files to describe, got none. Redirect to main manage sounds page.
        return HttpResponseRedirect(reverse('accounts-manage-sounds', args=['published']))
    forms = []
    forms_per_round = settings.SOUNDS_PER_DESCRIBE_ROUND
    all_forms_validated_ok = True
    all_remaining_sounds_to_edit_or_describe = files if describing else sounds
    sounds_to_edit_or_describe = all_remaining_sounds_to_edit_or_describe[:forms_per_round]
    len_original_describe_edit_sounds = request.session.get(f'{session_key_prefix}-len_original_describe_sounds', 0) if describing else request.session.get(f'{session_key_prefix}-len_original_edit_sounds', 0)
    num_rounds = int(math.ceil(len_original_describe_edit_sounds/forms_per_round))
    current_round = int((len_original_describe_edit_sounds - len(all_remaining_sounds_to_edit_or_describe))/forms_per_round + 1)
    files_data_for_players = []  # Used when describing sounds (not when editing) to be able to show sound players
    preselected_license = request.session.get(f'{session_key_prefix}-describe_license', False)  # Pre-selected from the license selection page when describing mulitple sounds
    preselected_pack = request.session.get(f'{session_key_prefix}-describe_pack', False)  # Pre-selected from the pack selection page when describing mulitple sounds
    
    for count, element in enumerate(sounds_to_edit_or_describe):
        prefix = str(count)
        if describing:
            audio_file_path = element.full_path
            duration = get_duration_from_processing_before_describe_files(audio_file_path)
            if duration > 0.0:
                processing_before_describe_base_url = get_processing_before_describe_sound_base_url(audio_file_path)
                file_data = {
                    'duration': duration,
                    'samplerate': get_samplerate_from_processing_before_describe_files(audio_file_path),
                    'preview_mp3': processing_before_describe_base_url + 'preview.mp3',
                    'preview_ogg': processing_before_describe_base_url + 'preview.ogg',
                    'wave': processing_before_describe_base_url + 'wave.png',
                    'spectral': processing_before_describe_base_url + 'spectral.png',
                }
                files_data_for_players.append(file_data)
            else:
                # If duration is 0.0, it might be because the file has not been processed-before-description yet
                # or there might have been problems while processing-before-description the sound. In that case
                # we won't show the player
                files_data_for_players.append(None)

        if request.method == "POST":
            form = SoundEditAndDescribeForm(
                request.POST, 
                prefix=prefix, 
                file_full_path=element.full_path if describing else None,
                explicit_disable=element.is_explicit if not describing else False,
                hide_old_license_versions="3.0" not in element.license.deed_url if not describing else True,
                user_packs=Pack.objects.filter(user=request.user if describing else element.user).exclude(is_deleted=True))
            forms.append(form)
            if form.is_valid():
                if not describing:
                    # Update sound object with new data. We add an extra check to make sure we don't mess up with
                    # the sounds stored in the session variables and the provided descriptions and we don't update
                    # the wrong sounds (which is a potential risk if users open the edit page in multiple tabs). By
                    # using this check we make sure we don't accidentally overwrite data (although it could happen
                    # that some of the edited data is not appleid at all)
                    sound_id_from_form = int(request.POST.get(f'{prefix}-sound_id', -1))
                    if sound_id_from_form == element.id:
                        update_edited_sound(element, form.cleaned_data)
                else:
                    # Don't do anything here except storing the audio filename from the POST data which will be later used
                    # as a double check to make sure we don't write the description to the wrong file
                    audio_filename_from_form = request.POST.get(f'{prefix}-audio_filename', None)
                    form.audio_filename_from_form = audio_filename_from_form 
            else:
                all_forms_validated_ok = False
            form.sound_sources_ids = list(form.cleaned_data['sources'])  # Add sources ids to list so sources sound selector can be initialized
            if describing:
                form.audio_filename = element.name
            else:
                form.sound_id = element.id
        else:
            if not describing:
                sound_sources_ids = list(element.get_sound_sources_as_set())
                initial = dict(tags=element.get_sound_tags_string(),
                            description=element.description,
                            name=element.original_filename,
                            license=element.license,
                            pack=element.pack.id if element.pack else None,
                            lat=element.geotag.lat if element.geotag else None,
                            lon=element.geotag.lon if element.geotag else None,
                            zoom=element.geotag.zoom if element.geotag else None,
                            sources=','.join([str(item) for item in sound_sources_ids]))
            else:
                sound_sources_ids = []
                initial = dict(name=os.path.splitext(element.name)[0])
                if preselected_license:
                    initial['license'] = preselected_license
                if preselected_pack:
                    initial['pack'] = preselected_pack.id
            form = SoundEditAndDescribeForm(
                prefix=prefix, 
                explicit_disable=element.is_explicit if not describing else False,
                initial=initial,
                hide_old_license_versions="3.0" not in element.license.deed_url if not describing else True,
                user_packs=Pack.objects.filter(user=request.user if describing else element.user).exclude(is_deleted=True))
            form.sound_sources_ids = sound_sources_ids
            if describing:
                form.audio_filename = element.name
            else:
                form.sound_id = element.id
            forms.append(form)  

    tvars = {
        'session_key_prefix': session_key_prefix,
        'describing': describing,
        'num_forms': len(forms),
        'forms': forms,
        'forms_have_errors': not all_forms_validated_ok,
        'sound_objects': sounds_to_edit_or_describe if not describing else None,
        'files_data_for_players': files_data_for_players,
        'current_round': current_round,
        'num_rounds': num_rounds,
        'sounds_per_round': forms_per_round,
        'last_latlong': request.user.profile.get_last_latlong(),
        'total_sounds_to_describe': len_original_describe_edit_sounds,
        'next': request.GET.get('next', '')
    }
    
    if request.method == "POST" and all_forms_validated_ok:
        if describing:
            # Create Sound objects, trigger moderation, processing, etc...
            create_sounds(request, forms)

            # Remove sounds successfully described from session data
            request.session[f'{session_key_prefix}-describe_sounds'] = files[forms_per_round:]

            # If no more sounds to describe, redirect to manage sound page, otherwise redirect to same page to proceed with second round
            messages.add_message(request, messages.INFO, 
                f'Successfully finished sound description round {current_round} of {num_rounds}!')
            if not request.session[f'{session_key_prefix}-describe_sounds']:
                clear_session_describe_data(request, session_key_prefix=session_key_prefix)
                return HttpResponseRedirect(reverse('accounts-manage-sounds', args=['processing']))
            else:
                return HttpResponseRedirect(reverse('accounts-describe-sounds') + f'?session={session_key_prefix}')
        else:
            # Remove sounds successfully described from session data
            request.session[f'{session_key_prefix}-edit_sounds'] = sounds[forms_per_round:]

            # If user was only editing one sound and has finished, clear session and redirect to the sound page
            if len(forms) == 1 and len_original_describe_edit_sounds == 1:
                clear_session_edit_data(request, session_key_prefix=session_key_prefix)
                redirect_to = request.GET.get('next', sounds[0].get_absolute_url())
                return HttpResponseRedirect(redirect_to)

            messages.add_message(request, messages.INFO, 
                f'Successfully finished sound editing round {current_round} of {num_rounds}!')
            if not request.session[f'{session_key_prefix}-edit_sounds']:
                # If no more sounds to edit, redirect to manage sounds page
                clear_session_edit_data(request, session_key_prefix=session_key_prefix)
                redirect_to = request.GET.get('next', reverse('accounts-manage-sounds', args=['published']))
                return HttpResponseRedirect(redirect_to)
            else:
                # Otherwise, redirect to the same page to continue with next round of sounds
                next_arg = request.GET.get('next', '')
                return HttpResponseRedirect(reverse('accounts-edit-sounds') + f'?next={next_arg}&session={session_key_prefix}')
        
    return render(request, 'sounds/edit_and_describe.html', tvars)


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
        form = PackEditForm(request.POST, instance=pack, label_suffix='')
        if form.is_valid():
            form.save()
            pack.sounds.all().update(is_index_dirty=True)
            redirect_to = request.GET.get('next', pack.get_absolute_url())
            return HttpResponseRedirect(redirect_to)
    else:
        form = PackEditForm(instance=pack, initial=dict(pack_sounds=pack_sounds), label_suffix='')
        current_sounds = Sound.objects.bulk_sounds_for_pack(pack_id=pack.id)
        form.pack_sound_objects = current_sounds
    tvars = {
        'pack': pack,
        'form': form,
        'current_sounds': current_sounds,
    }
    return render(request, 'sounds/pack_edit.html', tvars)


@login_required
def sound_edit_sources(request, username, sound_id):
    return HttpResponseRedirect(reverse('sound-edit', args=[username, sound_id]))


def add_sounds_modal_helper(request, username=None):
    tvars = {'sounds_to_select': [], 'q': request.GET.get('q', ''), 'search_executed': False}
    if request.GET.get('q', None) is not None:
        tvars['search_executed'] = True
        exclude_sound_ids = request.GET.get('exclude', '')
        if request.GET['q'] != '' or username is not None:
            query = request.GET['q']
            query_filter = ''
            if username is not None or exclude_sound_ids is not None:
                filter_parts = []
                if username is not None:
                    filter_parts.append(f'username:{username}')
                if exclude_sound_ids:
                    exclude_parts = []
                    for sound_id in exclude_sound_ids.split(','):
                        exclude_parts.append(f'id:{sound_id}')
                    exclude_part = 'NOT (' + ' OR '.join(exclude_parts) + ')'
                    filter_parts.append(exclude_part)
                query_filter = ' AND '.join(filter_parts)
            results, _ = perform_search_engine_query(
                {'textual_query': query, 'query_filter': query_filter, 'num_sounds': 9})
            tvars['sounds_to_select'] = [doc['id'] for doc in results.docs]
    return tvars


@login_required
def add_sounds_modal_for_pack_edit(request, pack_id):
    pack = get_object_or_404(Pack, id=pack_id)
    tvars = add_sounds_modal_helper(request, username=pack.user.username)
    tvars.update({
        'modal_title': 'Add sounds to pack',
        'help_text': 'Note that when adding a sound that already belongs to another pack it will be '
                     'removed from the former pack.',
    })
    return render(request, 'sounds/modal_add_sounds.html', tvars)


@login_required
def add_sounds_modal_for_edit_sources(request):
    tvars = add_sounds_modal_helper(request)
    tvars.update({
        'modal_title': 'Add sound sources',
    })
    return render(request, 'sounds/modal_add_sounds.html', tvars)

def _remix_group_view_helper(request, group_id):
    group = get_object_or_404(RemixGroup, id=group_id)
    data = group.protovis_data
    sounds = Sound.objects.ordered_ids(
        [element['id'] for element in group.sounds.all().order_by('created').values('id')])
    tvars = {
        'sounds': sounds,
        'last_sound': sounds[len(sounds)-1],
        'group_sound': sounds[0],
        'data': data
    }
    return tvars

@redirect_if_old_username_or_404
def remixes(request, username, sound_id):
    if not request.GET.get('ajax'):
        # If not loaded as modal, redirect to sound page with parameter to open modal
        return HttpResponseRedirect(reverse('sound', args=[username, sound_id]) + '?remixes=1')
    
    sound = get_object_or_404(Sound, id=sound_id, moderation_state="OK", processing_state="OK")
    if sound.user.username.lower() != username.lower():
        raise Http404
    try:
        remix_group = sound.remix_group.all()[0]
    except:
        raise Http404
    
    tvars = _remix_group_view_helper(request, remix_group.id)    
    tvars.update({'sound': sound})
    return render(request, 'sounds/modal_remix_group.html', tvars)


@redirect_if_old_username_or_404
@ratelimit(key=key_for_ratelimiting, rate=rate_per_ip, group=settings.RATELIMIT_SIMILARITY_GROUP, block=True)
def similar(request, username, sound_id):
    if not request.GET.get('ajax'):
        # If not loaded as modal, redirect to sound page with parameter to open modal
        return HttpResponseRedirect(reverse('sound', args=[username, sound_id]) + '?similar=1')

    sound = get_object_or_404(Sound,
                              id=sound_id,
                              moderation_state="OK",
                              processing_state="OK")
    if sound.user.username.lower() != username.lower():
        raise Http404

    num_similar_sounds = settings.NUM_SIMILAR_SOUNDS_PER_PAGE * settings.NUM_SIMILAR_SOUNDS_PAGES
    if not settings.USE_SEARCH_ENGINE_SIMILARITY:
        # Get similar sounds from similarity service (gaia)
        similarity_results, _ = get_similar_sounds(
            sound, request.GET.get('preset', None), num_similar_sounds)
    else:
        # Get similar sounds from solr
        try:
            results = get_search_engine().search_sounds(similar_to=sound.id,
                                                        similar_to_max_num_sounds=num_similar_sounds,
                                                        num_sounds=num_similar_sounds)
            similarity_results = [(result['id'], result['score']) for result in results.docs]
        except SearchEngineException:
            # Search engine not available, return empty list
            similarity_results = []
        
    paginator = paginate(request, [sound_id for sound_id, _ in similarity_results], settings.NUM_SIMILAR_SOUNDS_PER_PAGE)
    similar_sounds = Sound.objects.ordered_ids(paginator['page'].object_list)
    tvars = {'similar_sounds': similar_sounds, 'sound': sound}
    tvars.update(paginator)
    return render(request, 'sounds/modal_similar_sounds.html', tvars)


@redirect_if_old_username_or_404
@transaction.atomic()
def pack(request, username, pack_id):
    try:
        pack = Pack.objects.bulk_query_id(pack_id)[0]
        if pack.user.username.lower() != username.lower():
            raise Http404
    except (Pack.DoesNotExist, IndexError) as e:
        raise Http404

    if pack.is_deleted:
        return render(request, 'sounds/pack_deleted.html')

    qs = Sound.public.only('id').filter(pack=pack).order_by('-created')
    num_sounds_to_display = settings.SOUNDS_PER_PAGE_PROFILE_PACK_PAGE
    sound_ids = [sound_obj.id for sound_obj in qs[0:num_sounds_to_display]]
    pack_sounds = Sound.objects.ordered_ids(sound_ids)

    num_sounds_ok = qs.count()
    if num_sounds_ok < pack.num_sounds:
        messages.add_message(request, messages.INFO,
                             'Some sounds of this pack might <b>not have been moderated or processed</b> yet.')

    is_following = None
    geotags_in_pack_serialized = []
    is_following = request.user.is_authenticated and follow_utils.is_user_following_user(request.user, pack.user)
    if pack.has_geotags and settings.MAPBOX_USE_STATIC_MAPS_BEFORE_LOADING:
        for sound in Sound.public.select_related('geotag').filter(pack__id=pack_id).exclude(geotag=None):
            geotags_in_pack_serialized.append({'lon': sound.geotag.lon, 'lat': sound.geotag.lat})
        geotags_in_pack_serialized = json.dumps(geotags_in_pack_serialized)

    tvars = {
        'pack': pack,
        'pack_sounds': pack_sounds,
        'is_following': is_following,
        'geotags_in_pack_serialized': geotags_in_pack_serialized
    }
    return render(request, 'sounds/pack.html', tvars)


@redirect_if_old_username_or_404
def pack_stats_section(request, username, pack_id):
    if not request.GET.get('ajax'):
        raise Http404  # Only accessible via ajax
    try:
        pack = Pack.objects.bulk_query_id(pack_id)[0]
        if pack.user.username.lower() != username.lower():
            raise Http404
    except (Pack.DoesNotExist, IndexError) as e:
        raise Http404
    tvars = {
        'pack': pack,
    }
    return render(request, 'sounds/pack_stats_section.html', tvars)


@redirect_if_old_username_or_404
def packs_for_user(request, username):
    user = request.parameter_user
    return HttpResponseRedirect(user.profile.get_user_packs_in_search_url())


@redirect_if_old_username_or_404
def for_user(request, username):
    user = request.parameter_user
    return HttpResponseRedirect(user.profile.get_user_sounds_in_search_url())
    

@redirect_if_old_username_or_404
@transaction.atomic()
def flag(request, username, sound_id):
    if not request.GET.get('ajax'):
        # If not loaded as a modal, redirect to the sound page with parameter to open modal
        return HttpResponseRedirect(reverse('sound', args=[username, sound_id]) + '?flag=1')
    
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

            send_mail_template_to_support(settings.EMAIL_SUBJECT_SOUND_FLAG, "emails/email_flag.txt", {"flag": flag},
                                          extra_subject=f"{sound.user.username} - {sound.original_filename}",
                                          reply_to=user_email)
            return JsonResponse({'success': True})
    else:
        initial = {}
        if user:
            initial["email"] = user.email
        flag_form = FlagForm(initial=initial)

    tvars = {"sound": sound,
             "flag_form": flag_form}
    return render(request, 'sounds/modal_flag_sound.html', tvars)


def attribution_modal(request, username, sound_id):
    if not request.GET.get('ajax'):
        # If not loaded as a modal, redirect to the sound page with parameter to open modal
        return HttpResponseRedirect(reverse('sound', args=[username, sound_id]) + '?attribution=1')
    sound = get_object_or_404(Sound, id=sound_id)
    tvars = {'sound': sound}
    return render(request, 'sounds/modal_attribution.html', tvars)


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
    try:
        sound_obj = Sound.objects.bulk_query_id(sound_id)[0]
    except IndexError:
        raise Http404
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
        'request': request,
        'is_explicit': is_explicit,
        'is_authenticated': request.user.is_authenticated
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
        - 'full_size_no_info': like 'full_size' but without sound title/license and link to freesound.
          Eg: /embed/sound/iframe/1234/simple/full_size_no_info/.

    The sizes 'medium', 'medium_no_info', 'large', 'large_no_info' and 'full_size' can optionally show the spectrogram
    image instead of the waveform if being passed a request parameter 'spec=1' in the URL.
    Eg: /embed/sound/iframe/1234/simple/large/?spec=1.

    The sizes 'medium' and 'medium_no_info' can optionally show a button to toggle the background image between the
    waveform and the spectrogram by passing the request parameter 'td=1'. Bigger sizes always show that button.
    """
    if player_size not in ['mini', 'small', 'medium', 'large', 'large_no_info', 'medium_no_info', 'full_size', 'full_size_no_info']:
        raise Http404
    try:
        sound = Sound.objects.bulk_query_id_public(sound_id)[0]
    except IndexError:
        raise Http404
    tvars = {
        'sound': sound,
        'user_profile_locations': Profile.locations_static(sound.user_id, getattr(sound, 'user_has_avatar', False)),
        'username_and_filename': f'{sound.username} - {sound.original_filename}',
        'size': player_size,
        'use_spectrogram': request.GET.get('spec', None) == '1',
        'show_toggle_display_button': request.GET.get('td', None) == '1',
    }
    return render(request, 'embeds/sound_iframe.html', tvars)


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
    return render(request, 'embeds/sound_oembed.xml', tvars, content_type='text/xml')


def downloaders(request, username, sound_id):
    if not request.GET.get('ajax'):
        # If not loaded as a modal, redirect to sound page with parameter to open modal
        return HttpResponseRedirect(reverse('sound', args=[username, sound_id]) + '?downloaders=1')

    sound = get_object_or_404(Sound, id=sound_id)

    # Retrieve all users that downloaded a sound
    qs = Download.objects.filter(sound=sound_id)

    num_items_per_page = settings.USERS_PER_DOWNLOADS_MODAL_PAGE
    pagination = paginate(request, qs, num_items_per_page, object_count=sound.num_downloads)
    page = pagination["page"]

    # Get all users+profiles for the user ids
    userids = [d.user_id for d in list(page)]
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
    return render(request, 'sounds/modal_downloaders.html', tvars)


def pack_downloaders(request, username, pack_id):
    if not request.GET.get('ajax'):
         # If not loaded as a modal, redirect to sound page with parameter to open modal
        return HttpResponseRedirect(reverse('pack', args=[username, pack_id]) + '?downloaders=1')
    
    pack = get_object_or_404(Pack, id=pack_id)

    # Retrieve all users that downloaded a sound
    qs = PackDownload.objects.filter(pack_id=pack_id)
   
    num_items_per_page = settings.USERS_PER_DOWNLOADS_MODAL_PAGE
    pagination = paginate(request, qs, num_items_per_page, object_count=pack.num_downloads)
    page = pagination["page"]

    # Get all users+profiles for the user ids
    userids = [d.user_id for d in list(page)]
    users = User.objects.filter(pk__in=userids).select_related("profile")
    user_map = {}
    for u in users:
        user_map[u.id] = u

    download_list = []
    for s in page:
        download_list.append({"created": s.created, "user": user_map[s.user_id]})
    download_list = sorted(download_list, key=itemgetter("created"), reverse=True)

    tvars = {'username': username,
             'pack': pack,
             "download_list": download_list}
    tvars.update(pagination)
    return render(request, 'sounds/modal_downloaders.html', tvars)
