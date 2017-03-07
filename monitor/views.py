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
import json
import datetime

from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.cache import cache_page
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection
from django.db.models import Count, Sum
from django.shortcuts import redirect
from django.http import JsonResponse
from sounds.models import Sound
from tags.models import Tag, TaggedItem
import gearman
import tickets.views
import sounds.views
import forum.models
import ratings.models
import comments.models
import donations.models
@login_required
@user_passes_test(lambda u: u.is_staff, login_url='/')
def monitor_home(request):
    sounds_in_moderators_queue_count =\
        tickets.views._get_sounds_in_moderators_queue_count(request.user)

    new_upload_count = tickets.views.new_sound_tickets_count()
    tardy_moderator_sounds_count =\
        len(tickets.views._get_tardy_moderator_tickets())

    tardy_user_sounds_count = len(tickets.views._get_tardy_user_tickets())

    # Processing
    sounds_queued_count = sounds.views.Sound.objects.filter(
            processing_ongoing_state='QU').count()
    sounds_pending_count = sounds.views.Sound.objects.\
        filter(processing_state='PE')\
        .exclude(processing_ongoing_state='PR')\
        .exclude(processing_ongoing_state='QU')\
        .count()
    sounds_processing_count = sounds.views.Sound.objects.filter(
            processing_ongoing_state='PR').count()
    sounds_failed_count = sounds.views.Sound.objects.filter(
            processing_state='FA').count()
    sounds_ok_count = sounds.views.Sound.objects.filter(
            processing_state='OK').count()

    # Analysis
    sounds_analysis_pending_count = sounds.views.Sound.objects.filter(
        analysis_state='PE').count()
    sounds_analysis_queued_count = sounds.views.Sound.objects.filter(
        analysis_state='QU').count()
    sounds_analysis_ok_count = sounds.views.Sound.objects.filter(
        analysis_state='OK').count()
    sounds_analysis_failed_count = sounds.views.Sound.objects.filter(
        analysis_state='FA').count()
    sounds_analysis_skipped_count = sounds.views.Sound.objects.filter(
        analysis_state='SK').count()

    # Get gearman status
    try:
        gm_admin_client = gearman.GearmanAdminClient(settings.GEARMAN_JOB_SERVERS)
        gearman_status = gm_admin_client.get_status()
    except gearman.errors.ServerUnavailable:
        gearman_status = list()

    tvars = {"new_upload_count": new_upload_count,
             "tardy_moderator_sounds_count": tardy_moderator_sounds_count,
             "tardy_user_sounds_count": tardy_user_sounds_count,
             "sounds_queued_count": sounds_queued_count,
             "sounds_pending_count": sounds_pending_count,
             "sounds_processing_count": sounds_processing_count,
             "sounds_failed_count": sounds_failed_count,
             "sounds_ok_count": sounds_ok_count,
             "sounds_analysis_pending_count": sounds_analysis_pending_count,
             "sounds_analysis_queued_count": sounds_analysis_queued_count,
             "sounds_analysis_ok_count": sounds_analysis_ok_count,
             "sounds_analysis_failed_count": sounds_analysis_failed_count,
             "sounds_analysis_skipped_count": sounds_analysis_skipped_count,
             "gearman_status": gearman_status,
             "sounds_in_moderators_queue_count": sounds_in_moderators_queue_count
    }

    return render(request, 'monitor/monitor.html', tvars)


@cache_page(60 * 60 * 24)
def sounds_stats_ajax(request):
    time_span = datetime.datetime.now()-datetime.timedelta(weeks=2)

    new_sounds_mod = sounds.models.Sound.objects\
            .filter(created__gt=time_span, moderation_date__isnull=False)\
            .extra(select={'day': 'date(moderation_date)'}).values('day')\
            .order_by().annotate(Count('id'))

    new_sounds = sounds.models.Sound.objects\
            .filter(created__gt=time_span, processing_date__isnull=False)\
            .extra(select={'day': 'date(processing_date)'}).values('day')\
            .order_by().annotate(Count('id'))

    return JsonResponse({
        "new_sounds_mod": list(new_sounds_mod),
        "new_sounds": list(new_sounds)
        })


@cache_page(60 * 60 * 24)
def users_stats_ajax(request):
    time_span = datetime.datetime.now()-datetime.timedelta(weeks=2)

    new_users = User.objects.filter(date_joined__gt=time_span)\
            .extra(select={'day': 'date(date_joined)'})\
            .values('day', 'is_active').order_by().annotate(Count('id'))

    return JsonResponse({
        "new_users": list(new_users),
        })


@cache_page(60 * 60 * 24)
def downloads_stats_ajax(request):
    time_span = datetime.datetime.now()-datetime.timedelta(weeks=2)

    new_downloads_sound = sounds.models.Download.objects\
            .filter(created__gt=time_span, pack=None)\
            .extra({'day': 'date(created)'}).values('day').order_by()\
            .annotate(Count('id'))

    new_downloads_pack = sounds.models.Download.objects\
            .filter(created__gt=time_span, sound=None)\
            .extra({'day': 'date("sounds_download".created)'}).values('day').order_by()\
            .annotate(id__count=Sum('pack__num_sounds'))

    return JsonResponse({
        'new_downloads_sound': list(new_downloads_sound),
        'new_downloads_pack': list(new_downloads_pack),
        })


@cache_page(60 * 60 * 24)
def donations_stats_ajax(request):
    time_span = datetime.datetime.now()-datetime.timedelta(days=365)

    query_donations = donations.models.Donation.objects\
            .filter(created__gt=time_span)\
            .extra({'week': "to_char(created, 'WW-IYYY')"})\
            .values('week').order_by()\
            .annotate(Sum('amount'))
    new_donations = [{
        'week': str(datetime.datetime.strptime(d['week']+ '-0', "%W-%Y-%w").date()),
        'amount__sum': d['amount__sum']
        } for d in query_donations]

    return JsonResponse({
        'new_donations': new_donations,
        })


@cache_page(60 * 60 * 24)
def tags_stats_ajax(request):
    time_span = datetime.datetime.now()-datetime.timedelta(weeks=2)

    top_tags = TaggedItem.objects.filter(created__gt=time_span)\
            .values('tag_id').distinct().annotate(num=Count('tag_id'))\
            .order_by('-num')[:30]
    top_tags = [t['tag_id'] for t in  top_tags]
    tags_stats = TaggedItem.objects\
            .filter(tag_id__in=top_tags, created__gt=time_span)\
            .extra(select={'day': 'date(created)'})\
            .values('day', 'tag__name').order_by().annotate(Count('tag_id'))

    tags = {i['tag__name']: [] for i in tags_stats}
    for i in tags_stats:
        tags[i['tag__name']].append({
            'count': i['tag_id__count'],
            'day': i['day']
        })
    return JsonResponse({"tags_stats":tags})

@cache_page(60 * 60 * 24)
def total_users_stats_ajax(request):
    users = User.objects.filter(is_active=True)
    users_num = users.count()
    users_with_sounds = users.filter(profile__num_sounds__gt=0).count()
    num_donations = donations.models.Donation.objects\
            .aggregate(Sum('amount'))['amount__sum']
    return JsonResponse({
        "total_users": users_num,
        "users_with_sounds": users_with_sounds,
        "total_donations": num_donations,
        })


@cache_page(60 * 60 * 24)
def total_sounds_stats_ajax(request):
    num_sounds = sounds.models.Sound.objects.filter(processing_state="OK",
            moderation_state="OK").count()
    packs = sounds.models.Pack.objects.all().count()
    return JsonResponse({
        "sounds": num_sounds,
        "packs": packs,
        })


@cache_page(60 * 60 * 24)
def total_activity_stats_ajax(request):
    downloads = sounds.models.Download.objects.all().count()
    num_comments = comments.models.Comment.objects.all().count()
    num_ratings = ratings.models.Rating.objects.all().count()
    return JsonResponse({
        "downloads": downloads,
        "comments": num_comments,
        "ratings": num_ratings,
        })

@cache_page(60 * 60 * 24)
def total_tags_stats_ajax(request):
    tags = Tag.objects.all().count()
    tags_used = TaggedItem.objects.all().count()
    return JsonResponse({
        "tags": tags,
        "tags_used": tags_used,
        })


@cache_page(60 * 60 * 24)
def total_forum_stats_ajax(request):
    posts = forum.models.Post.objects.all().count()
    threads = forum.models.Thread.objects.all().count()

    return JsonResponse({
        "posts": posts,
        "threads": threads,
        })

@login_required
@user_passes_test(lambda u: u.is_staff, login_url='/')
def process_sounds(request):

    # Send sounds to processing according to their processing_state
    processing_status = request.GET.get('prs', None)
    if processing_status:
        sounds_to_process = None
        if processing_status in ['FA', 'PE']:
            sounds_to_process = Sound.objects.filter(processing_state=processing_status)

        # Remove sounds from the list that are already in the queue or are being processed right now
        if sounds_to_process:
            sounds_to_process = sounds_to_process.exclude(processing_ongoing_state='PR')\
                .exclude(processing_ongoing_state='QU')
            for sound in sounds_to_process:
                sound.process()

    # Send sounds to processing according to their processing_ongoing_state
    processing_ongoing_state = request.GET.get('pros', None)
    if processing_ongoing_state:
        sounds_to_process = None
        if processing_ongoing_state in ['QU', 'PR']:
            sounds_to_process = Sound.objects.filter(processing_ongoing_state=processing_ongoing_state)

        if sounds_to_process:
            for sound in sounds_to_process:
                sound.process()

    # Send sounds to analysis according to their analysis_state
    analysis_state = request.GET.get('ans', None)
    if analysis_state:
        sounds_to_analyze = None
        if analysis_state in ['QU', 'PE', 'FA', 'SK']:
            sounds_to_analyze = Sound.objects.filter(analysis_state=analysis_state)

        if sounds_to_analyze:
            for sound in sounds_to_analyze:
                sound.process()

    return redirect("monitor-home")
