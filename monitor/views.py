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
from collections import Counter

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Count
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse

import tickets
from freesound.celery import get_queues_task_counts
from sounds.models import Sound, SoundAnalysis
from tickets import TICKET_STATUS_CLOSED
from utils.frontend_handling import render, using_beastwhoosh, redirect_if_beastwhoosh


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='/')
def get_queues_status(request):
    try:
        celery_task_counts = get_queues_task_counts()
    except Exception:
        celery_task_counts = []
    return render(request, 'monitor/queues_status.html',
                  {'celery_task_counts': celery_task_counts})


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='/')
def monitor_home(request):
    if using_beastwhoosh(request):
        return redirect("monitor-stats")

    sounds_in_moderators_queue_count =\
        tickets.views._get_sounds_in_moderators_queue_count(request.user)

    new_upload_count = tickets.views.new_sound_tickets_count()
    tardy_moderator_sounds_count =\
        len(tickets.views._get_tardy_moderator_tickets())

    tardy_user_sounds_count = len(tickets.views._get_tardy_user_tickets())

    # Processing
    sounds_queued_count = Sound.objects.filter(
            processing_ongoing_state='QU').count()
    sounds_pending_count = Sound.objects.\
        filter(processing_state='PE')\
        .exclude(processing_ongoing_state='PR')\
        .exclude(processing_ongoing_state='QU')\
        .count()
    sounds_processing_count = Sound.objects.filter(
            processing_ongoing_state='PR').count()
    sounds_failed_count = Sound.objects.filter(
            processing_state='FA').count()
    sounds_ok_count = Sound.objects.filter(
            processing_state='OK').count()

    # Analysis
    analyzers_data = {}  
    all_sound_ids = Sound.objects.all().values_list('id', flat=True).order_by('id')
    n_sounds = len(all_sound_ids)
    for analyzer_name in settings.ANALYZERS_CONFIGURATION.keys():
        ok = SoundAnalysis.objects.filter(analyzer=analyzer_name, analysis_status="OK").count()
        sk = SoundAnalysis.objects.filter(analyzer=analyzer_name, analysis_status="SK").count()
        fa = SoundAnalysis.objects.filter(analyzer=analyzer_name, analysis_status="FA").count()
        qu = SoundAnalysis.objects.filter(analyzer=analyzer_name, analysis_status="QU").count()
        missing = n_sounds - (ok + sk + fa + qu)
        percentage_done = (ok + sk + fa) * 100.0/n_sounds
        analyzers_data[analyzer_name] = {
            'OK': ok,
            'SK': sk,
            'FA': fa,
            'QU': qu,
            'Missing': missing,
            'Percentage': percentage_done,
        }

    tvars = {"new_upload_count": new_upload_count,
             "tardy_moderator_sounds_count": tardy_moderator_sounds_count,
             "tardy_user_sounds_count": tardy_user_sounds_count,
             "sounds_queued_count": sounds_queued_count,
             "sounds_pending_count": sounds_pending_count,
             "sounds_processing_count": sounds_processing_count,
             "sounds_failed_count": sounds_failed_count,
             "sounds_ok_count": sounds_ok_count,
             "sounds_in_moderators_queue_count": sounds_in_moderators_queue_count,
             "analyzers_data": [(key, value) for key, value in analyzers_data.items()],
             "queues_stats_url": reverse('queues-stats'),
    }

    return render(request, 'monitor/monitor.html', tvars)


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='/')
def monitor_processing(request):
    # Processing
    sounds_queued_count = Sound.objects.filter(
            processing_ongoing_state='QU').count()
    sounds_pending_count = Sound.objects.\
        filter(processing_state='PE')\
        .exclude(processing_ongoing_state='PR')\
        .exclude(processing_ongoing_state='QU')\
        .count()
    sounds_processing_count = Sound.objects.filter(
            processing_ongoing_state='PR').count()
    sounds_failed_count = Sound.objects.filter(
            processing_state='FA').count()
    sounds_ok_count = Sound.objects.filter(
            processing_state='OK').count()
    tvars = {
        "sounds_queued_count": sounds_queued_count,
        "sounds_pending_count": sounds_pending_count,
        "sounds_processing_count": sounds_processing_count,
        "sounds_failed_count": sounds_failed_count,
        "sounds_ok_count": sounds_ok_count,
        "queues_stats_url": reverse('queues-stats'),
        "activePage": "processing"
    }
    return render(request, 'monitor/processing.html', tvars)

@login_required
@user_passes_test(lambda u: u.is_staff, login_url='/')
def monitor_analysis(request):
    # Analysis
    analyzers_data = {}  
    all_sound_ids = Sound.objects.all().values_list('id', flat=True).order_by('id')
    n_sounds = len(all_sound_ids)
    for analyzer_name in settings.ANALYZERS_CONFIGURATION.keys():
        ok = SoundAnalysis.objects.filter(analyzer=analyzer_name, analysis_status="OK").count()
        sk = SoundAnalysis.objects.filter(analyzer=analyzer_name, analysis_status="SK").count()
        fa = SoundAnalysis.objects.filter(analyzer=analyzer_name, analysis_status="FA").count()
        qu = SoundAnalysis.objects.filter(analyzer=analyzer_name, analysis_status="QU").count()
        missing = n_sounds - (ok + sk + fa + qu)
        percentage_done = (ok + sk + fa) * 100.0/n_sounds
        analyzers_data[analyzer_name] = {
            'OK': ok,
            'SK': sk,
            'FA': fa,
            'QU': qu,
            'Missing': missing,
            'Percentage': percentage_done,
        }
    tvars = {
        "analyzers_data": [(key, value) for key, value in analyzers_data.items()],
        "queues_stats_url": reverse('queues-stats'),
        "activePage": "analysis"
    }
    return render(request, 'monitor/analysis.html', tvars)


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='/')
def monitor_moderation(request):
    sounds_in_moderators_queue_count =\
        tickets.views._get_sounds_in_moderators_queue_count(request.user)
    new_upload_count = tickets.views.new_sound_tickets_count()
    tardy_moderator_sounds_count =\
        len(tickets.views._get_tardy_moderator_tickets())
    tardy_user_sounds_count = len(tickets.views._get_tardy_user_tickets())

    time_span = datetime.datetime.now() - datetime.timedelta((6 * 365) // 12)
    #Maybe we should user created and not modified
    user_ids = tickets.models.Ticket.objects.filter(
            status=TICKET_STATUS_CLOSED,
            created__gt=time_span,
            assignee__isnull=False
    ).values_list("assignee_id", flat=True)
    counter = Counter(user_ids)
    moderators = User.objects.filter(id__in=list(counter.keys()))
    moderators = [(counter.get(m.id), m) for m in moderators.all()]
    ordered = sorted(moderators, key=lambda m: m[0], reverse=True)


    tvars = {
        "new_upload_count": new_upload_count,
        "tardy_moderator_sounds_count": tardy_moderator_sounds_count,
        "tardy_user_sounds_count": tardy_user_sounds_count,
        "sounds_in_moderators_queue_count": sounds_in_moderators_queue_count,
        "moderators": ordered,
        "activePage": "moderation"
    }
    return render(request, 'monitor/moderation.html', tvars)


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='/')
def monitor_stats(request):
    tvars = {"activePage": "stats"}
    return render(request, 'monitor/stats.html', tvars)


@redirect_if_beastwhoosh('monitor-moderation')
@login_required
@user_passes_test(lambda u: u.is_staff, login_url='/')
def moderators_stats(request):
    time_span = datetime.datetime.now() - datetime.timedelta((6 * 365) // 12)
    #Maybe we should user created and not modified
    user_ids = tickets.models.Ticket.objects.filter(
            status=TICKET_STATUS_CLOSED,
            created__gt=time_span,
            assignee__isnull=False
    ).values_list("assignee_id", flat=True)

    counter = Counter(user_ids)
    moderators = User.objects.filter(id__in=list(counter.keys()))

    moderators = [(counter.get(m.id), m) for m in moderators.all()]
    ordered = sorted(moderators, key=lambda m: m[0], reverse=True)
    tvars = {"moderators": ordered}
    return render(request, 'monitor/moderators_stats.html', tvars)


def queries_stats_ajax(request):
    try:
        auth = (settings.GRAYLOG_USERNAME, settings.GRAYLOG_PASSWORD)
        params = {
            'query': '*',
            'range': 14 * 60 * 60 * 24,
            'filter': f'streams:{settings.GRAYLOG_SEARCH_STREAM_ID}',
            'field': 'query'
        }
        req = requests.get(settings.GRAYLOG_DOMAIN + '/graylog/api/search/universal/relative/terms',
                auth=auth, params=params)
        req.raise_for_status()
        return JsonResponse(req.json())
    except requests.HTTPError:
        return HttpResponse(status=500)
    except ValueError:
        return HttpResponse(status=500)


def tags_stats_ajax(request):
    tags_stats = cache.get("tags_stats")
    return JsonResponse(tags_stats or {})


def sounds_stats_ajax(request):
    sounds_stats = cache.get("sounds_stats")
    return JsonResponse(sounds_stats or {})


def active_users_stats_ajax(request):
    active_users_stats = cache.get("active_users_stats")
    return JsonResponse(active_users_stats or {})


def users_stats_ajax(request):
    users_stats = cache.get("users_stats")
    return JsonResponse(users_stats or {})


def downloads_stats_ajax(request):
    downloads_stats = cache.get("downloads_stats")
    return JsonResponse(downloads_stats or {})


def donations_stats_ajax(request):
    donations_stats = cache.get("donations_stats")
    return JsonResponse(donations_stats or {})


def totals_stats_ajax(request):
    totals_stats = cache.get("totals_stats")
    return JsonResponse(totals_stats or {})


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
                sound.process(force=True)

    # Send sounds to processing according to their processing_ongoing_state
    processing_ongoing_state = request.GET.get('pros', None)
    if processing_ongoing_state:
        sounds_to_process = None
        if processing_ongoing_state in ['QU', 'PR']:
            sounds_to_process = Sound.objects.filter(processing_ongoing_state=processing_ongoing_state)

        if sounds_to_process:
            for sound in sounds_to_process:
                sound.process(force=True)
    
    if using_beastwhoosh(request):
        return redirect("monitor-processing")
    return redirect("monitor-home")


def moderator_stats_ajax(request):
    user_id = request.GET.get('user_id', None)
    time_span = datetime.datetime.now() - datetime.timedelta((6 * 365) // 12)
    tickets_mod = tickets.models.Ticket.objects.filter(
            assignee_id=user_id,
            status=TICKET_STATUS_CLOSED,
            created__gt=time_span
    ).extra(select={'day': 'date(modified)'}).values('day')\
            .order_by().annotate(Count('id'))

    return JsonResponse(list(tickets_mod), safe=False)
