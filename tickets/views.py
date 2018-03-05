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
import gearman
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core.management import call_command
from django.db import connection, transaction
from django.db.models import Count, Min, Max, Q, F
from django.contrib import messages
from django.conf import settings
from models import Ticket, Queue, TicketComment, UserAnnotation
from forms import *
from tickets import *
from sounds.models import Sound
from utils.cache import invalidate_template_cache
from utils.pagination import paginate


def _get_tc_form(request, use_post=True):
    return _get_anon_or_user_form(request, AnonymousMessageForm, UserMessageForm, use_post)


def _get_anon_or_user_form(request, anonymous_form, user_form, use_post=True):
    if _can_view_mod_msg(request) and anonymous_form != AnonymousContactForm:
        user_form = ModeratorMessageForm
    if len(request.POST.keys()) > 0 and use_post:
        if request.user.is_authenticated:
            return user_form(request.POST)
        else:
            return anonymous_form(request.POST)
    else:
        return user_form() if request.user.is_authenticated else anonymous_form()


def _can_view_mod_msg(request):
    return request.user.is_authenticated \
            and (request.user.is_superuser or request.user.is_staff \
                 or Group.objects.get(name='moderators') in request.user.groups.all())


# TODO: copied from sound_edit view,
def is_selected(request, prefix):
    for name in request.POST.keys():
        if name.startswith(prefix):
            return True
    return False


def invalidate_all_moderators_header_cache():
    mods = Group.objects.get(name='moderators').user_set.all()
    for mod in mods:
        invalidate_template_cache("user_header", mod.id)


def ticket(request, ticket_key):
    can_view_moderator_only_messages = _can_view_mod_msg(request)
    clean_status_forms = True
    clean_comment_form = True
    ticket = get_object_or_404(Ticket.objects.select_related('sound__license', 'sound__user'), key=ticket_key)

    if request.method == 'POST':

        invalidate_template_cache("user_header", ticket.sender.id)
        invalidate_all_moderators_header_cache()

        # Left ticket message
        if is_selected(request, 'recaptcha') or (request.user.is_authenticated and is_selected(request, 'message')):
            tc_form = _get_tc_form(request)
            if tc_form.is_valid():
                tc = TicketComment()
                tc.text = tc_form.cleaned_data['message']
                tc.moderator_only = tc_form.cleaned_data.get('moderator_only', False)
                if tc.text:
                    if request.user.is_authenticated:
                        tc.sender = request.user
                    tc.ticket = ticket
                    tc.save()
                    if not request.user.is_authenticated:
                        email_to = Ticket.MODERATOR_ONLY
                    elif request.user == ticket.sender:
                        email_to = Ticket.MODERATOR_ONLY
                    else:
                        email_to = Ticket.USER_ONLY
                    ticket.send_notification_emails(ticket.NOTIFICATION_UPDATED,
                                                    email_to)
            else:
                clean_comment_form = False
        # update sound ticket
        elif is_selected(request, 'tm') or is_selected(request, 'ss'):
            ticket_form = TicketModerationForm(request.POST, prefix="tm")
            sound_form = SoundStateForm(request.POST, prefix="ss")
            if ticket_form.is_valid() and sound_form.is_valid():
                clean_status_forms = True
                clean_comment_form = True
                sound_state = sound_form.cleaned_data.get('state')
                # Sound should be deleted
                if sound_state == 'DE':
                    if ticket.sound:
                        ticket.sound.delete()
                        ticket.sound = None
                    ticket.status = TICKET_STATUS_CLOSED
                    tc = TicketComment(sender=request.user,
                                       text="Moderator %s deleted the sound and closed the ticket" % request.user,
                                       ticket=ticket,
                                       moderator_only=False)
                    tc.save()
                    ticket.send_notification_emails(ticket.NOTIFICATION_DELETED,
                                                    ticket.USER_ONLY)
                # Set another sound state that's not delete
                else:
                    if ticket.sound:
                        ticket.sound.moderation_state = sound_state
                        # Mark the index as dirty so it'll be indexed in Solr
                        if sound_state == "OK":
                            ticket.sound.mark_index_dirty()
                        ticket.sound.save()
                    ticket.status = ticket_form.cleaned_data.get('status')
                    tc = TicketComment(sender=request.user,
                                       text="Moderator %s set the sound to %s and the ticket to %s." %
                                            (request.user,
                                             'pending' if sound_state == 'PE' else sound_state,
                                             ticket.status),
                                       ticket=ticket,
                                       moderator_only=False)
                    tc.save()
                    ticket.send_notification_emails(ticket.NOTIFICATION_UPDATED,
                                                    ticket.USER_ONLY)
                ticket.save()

    if clean_status_forms:
        ticket_form = TicketModerationForm(initial={'status': ticket.status}, prefix="tm")
        state = ticket.sound.moderation_state if ticket.sound else 'DE'
        sound_form = SoundStateForm(initial={'state': state}, prefix="ss")
    if clean_comment_form:
        tc_form = _get_tc_form(request, False)

    num_sounds_pending = ticket.sender.profile.num_sounds_pending_moderation()
    tvars = {"ticket": ticket,
             "num_sounds_pending": num_sounds_pending,
             "tc_form": tc_form,
             "ticket_form": ticket_form,
             "sound_form": sound_form,
             "can_view_moderator_only_messages": can_view_moderator_only_messages}
    return render(request, 'tickets/ticket.html', tvars)


# In the next 2 functions we return a queryset os the evaluation is lazy.
# N.B. these functions are used in the home page as well.
def new_sound_tickets_count():

    return len(Ticket.objects.filter(assignee=None, sound__moderation_state='PE',
            sound__processing_state='OK', status=TICKET_STATUS_NEW))

@login_required
def sound_ticket_messages(request, ticket_key):
    can_view_moderator_only_messages = _can_view_mod_msg(request)
    ticket = get_object_or_404(Ticket, key=ticket_key)
    tvars = {"can_view_moderator_only_messages": can_view_moderator_only_messages,
             "ticket": ticket}
    return render(request, 'tickets/message_list.html', tvars)


def _get_new_uploaders_by_ticket():

    tickets = Ticket.objects.filter(
        sound__processing_state='OK',
        sound__moderation_state='PE',
        assignee=None,
        status=TICKET_STATUS_NEW).values('sender')\
                                 .annotate(total=Count('sender'), older=Min('created'))\
                                 .order_by('older')

    users = User.objects.filter(id__in=[t['sender'] for t in tickets]).select_related('profile')
    users_dict = {u.id: u for u in users}
    new_sounds_users = []

    for t in tickets:
        new_sounds_users.append((
            users_dict[t['sender']],
            t['total'],
            (datetime.datetime.now() - t['older']).days
        ))

    return new_sounds_users


def _get_unsure_sound_tickets():
    """Query to get tickets that were returned to the queue by moderators that
    didn't know what to do with the sound."""
    return Ticket.objects.filter(
                                 assignee=None,
                                 status=TICKET_STATUS_ACCEPTED)


def _get_tardy_moderator_tickets():
    """Get tickets for moderators that haven't responded in the last day"""
    time_span = datetime.date.today() - datetime.timedelta(days=1)

    tt = Ticket.objects.filter(
        Q(assignee__isnull=False) &
        ~Q(status=TICKET_STATUS_CLOSED) &
        (Q(last_commenter=F('sender')) | Q(messages__sender=None)) &
        Q(comment_date__lt=time_span)
    )
    return tt


def _get_tardy_user_tickets():
    """Get tickets for users that haven't responded in the last 2 days"""
    time_span = datetime.date.today() - datetime.timedelta(days=2)

    tt = Ticket.objects.filter(
        Q(assignee__isnull=False) &
        ~Q(status=TICKET_STATUS_CLOSED) &
        ~Q(last_commenter=F('sender')) &
        Q(comment_date__lt=time_span)
    )
    return tt


def _get_sounds_in_moderators_queue_count(user):
    return Ticket.objects.select_related() \
        .filter(assignee=user.id) \
        .exclude(status='closed') \
        .exclude(sound=None) \
        .order_by('status', '-created').count()


@permission_required('tickets.can_moderate')
def moderation_home(request):
    sounds_in_moderators_queue_count = _get_sounds_in_moderators_queue_count(request.user)

    new_sounds_users = _get_new_uploaders_by_ticket()
    unsure_tickets = _get_unsure_sound_tickets()

    tardy_moderator_tickets = _get_tardy_moderator_tickets()
    tardy_user_tickets = _get_tardy_user_tickets()
    tardy_moderator_tickets_count = len(tardy_moderator_tickets)
    tardy_user_tickets_count = len(tardy_user_tickets)

    tvars = {"new_sounds_users": new_sounds_users,
             "unsure_tickets": unsure_tickets,
             "tardy_moderator_tickets": tardy_moderator_tickets[:5],
             "tardy_user_tickets": tardy_user_tickets[:5],
             "tardy_moderator_tickets_count": tardy_moderator_tickets_count,
             "tardy_user_tickets_count": tardy_user_tickets_count,
             "moderator_tickets_count": sounds_in_moderators_queue_count,
             "selected": "assigned"
            }

    return render(request, 'tickets/moderation_home.html', tvars)


@permission_required('tickets.can_moderate')
def moderation_tardy_users_sounds(request):
    sounds_in_moderators_queue_count = _get_sounds_in_moderators_queue_count(request.user)
    tardy_user_tickets = _get_tardy_user_tickets()
    paginated = paginate(request, tardy_user_tickets, 10)

    tvars = {"moderator_tickets_count": sounds_in_moderators_queue_count,
             "tardy_user_tickets": tardy_user_tickets,
             "selected": "assigned"}
    tvars.update(paginated)

    return render(request, 'tickets/moderation_tardy_users.html', tvars)


@permission_required('tickets.can_moderate')
def moderation_tardy_moderators_sounds(request):
    sounds_in_moderators_queue_count = _get_sounds_in_moderators_queue_count(request.user)
    tardy_moderators_tickets = _get_tardy_moderator_tickets()
    paginated = paginate(request, tardy_moderators_tickets, 10)

    tvars = {"moderator_tickets_count": sounds_in_moderators_queue_count,
             "tardy_moderators_tickets": tardy_moderators_tickets,
             "selected": "assigned"}
    tvars.update(paginated)

    return render(request, 'tickets/moderation_tardy_moderators.html', tvars)


@permission_required('tickets.can_moderate')
def moderation_assign_user(request, user_id):
    sender = User.objects.get(id=user_id)

    Ticket.objects.filter(sound__processing_state='OK',\
            sound__moderation_state='PE', assignee=None,\
            status=TICKET_STATUS_NEW, sound__user=sender).update(\
                assignee=request.user,\
                status=TICKET_STATUS_ACCEPTED,\
                modified=datetime.datetime.now())

    msg = 'You have been assigned all new sounds from %s.' % sender.username
    messages.add_message(request, messages.INFO, msg)
    invalidate_all_moderators_header_cache()

    return redirect("tickets-moderation-home")


@permission_required('tickets.can_moderate')
@transaction.atomic()
def moderation_assign_single_ticket(request, user_id, ticket_id):
    # REASSIGN SINGLE TICKET
    ticket = Ticket.objects.get(id=ticket_id)
    ticket.assignee = User.objects.get(id=request.user.id)

    # update modified date, so it doesn't appear in tardy moderator's sounds
    ticket.modified = datetime.datetime.now()
    ticket.save()
    invalidate_all_moderators_header_cache()

    msg = 'You have been assigned ticket "%s".' % ticket.title
    messages.add_message(request, messages.INFO, msg)

    next = request.GET.get("next", None)
    p = request.GET.get("p", 1)

    if next:
        if next == "tardy_users":
            return redirect("tickets-moderation-tardy-users")
        elif next == "tardy_moderators":
            return redirect(reverse("tickets-moderation-tardy-moderators")+"?page=%s" % p)
        elif next == "ticket":
            return redirect(reverse("tickets-ticket", kwargs={'ticket_key': ticket.key}))
        else:
            return redirect(reverse("tickets-moderation-home")+"?page=%s" % p)
    else:
        return redirect("tickets-moderation-home")


@permission_required('tickets.can_moderate')
@transaction.atomic()
def moderation_assigned(request, user_id):

    clear_forms = True
    if request.method == 'POST':
        mod_sound_form = SoundModerationForm(request.POST)
        msg_form = ModerationMessageForm(request.POST)

        if mod_sound_form.is_valid() and msg_form.is_valid():
            ticket_ids = mod_sound_form.cleaned_data.get("ticket", '').split('|')
            tickets = Ticket.objects.filter(id__in=ticket_ids)
            msg = msg_form.cleaned_data.get("message", False)
            action = mod_sound_form.cleaned_data.get("action")

            notification = None
            users_to_update = set()
            packs_to_update = set()

            if action == "Approve":
                tickets.update(status=TICKET_STATUS_CLOSED)
                explicit = mod_sound_form.cleaned_data.get("is_explicit")
                Sound.objects.filter(ticket__in=tickets).update(
                        is_index_dirty=True,
                        moderation_state='OK',
                        moderation_date=datetime.datetime.now(),
                        is_explicit=explicit)
                if msg:
                    notification = Ticket.NOTIFICATION_APPROVED_BUT
                else:
                    notification = Ticket.NOTIFICATION_APPROVED

            elif action == "Defer":
                tickets.update(status=TICKET_STATUS_DEFERRED)

                # only send a notification if a message was added
                if msg:
                    notification = Ticket.NOTIFICATION_QUESTION

            elif action == "Return":
                tickets.update(status=TICKET_STATUS_NEW, assignee=None)
                # no notification here

            elif action == "Delete":
                # to prevent a crash if the form is resubmitted
                tickets.update(status=TICKET_STATUS_CLOSED)
                # if tickets are being deleted we have to fill users_to_update
                # and sounds_to_update before we delete the sounds and they dissapear
                # from the ticket (thus losing reference)
                for ticket in tickets:
                    users_to_update.add(ticket.sound.user.profile)
                    if ticket.sound.pack:
                        packs_to_update.add(ticket.sound.pack)
                Sound.objects.filter(ticket__in=tickets).delete()
                # After we delete sounds that these tickets are associated with,
                # we refresh the ticket list so that sound_id is null and this does
                # not affect the TicketComment post_save trigger
                tickets = Ticket.objects.filter(id__in=ticket_ids)
                notification = Ticket.NOTIFICATION_DELETED

            elif action == "Whitelist":
                ticket_ids = list(tickets.values_list('id',flat=True))
                gm_client = gearman.GearmanClient(settings.GEARMAN_JOB_SERVERS)
                gm_client.submit_job("whitelist_user", json.dumps(ticket_ids),
                        wait_until_complete=False, background=True)
                notification = Ticket.NOTIFICATION_WHITELISTED

                users = set(tickets.values_list('sender__username', flat=True))
                messages.add_message(request, messages.INFO,
                    """User(s) %s has/have been whitelisted. Some of tickets might
                    still appear on this list for some time. Please reload the
                    page in a few seconds to see the updated list of pending
                    tickets""" % ", ".join(users))

            for ticket in tickets:
                if action != "Delete":
                    # We only fill here users_to_update and packs_to_update if action is not
                    # "Delete". See comment in "Delete" action case some lines above
                    users_to_update.add(ticket.sound.user.profile)
                    if ticket.sound.pack:
                        packs_to_update.add(ticket.sound.pack)
                invalidate_template_cache("user_header", ticket.sender.id)
                invalidate_all_moderators_header_cache()
                moderator_only = msg_form.cleaned_data.get("moderator_only", False)

                if msg:
                    tc = TicketComment(sender=ticket.assignee,
                                       text=msg,
                                       ticket=ticket,
                                       moderator_only=moderator_only)
                    tc.save()

                # Send emails
                if notification:
                    ticket.send_notification_emails(notification, Ticket.USER_ONLY)

            # Update number of sounds for each user
            for profile in users_to_update:
                profile.update_num_sounds()

            # Process packs
            for pack in packs_to_update:
                pack.process()
        else:
            clear_forms = False
    if clear_forms:
        mod_sound_form = SoundModerationForm(initial={'action': 'Approve'})
        msg_form = ModerationMessageForm()

    qs = Ticket.objects.select_related() \
                       .filter(assignee=user_id) \
                       .exclude(status=TICKET_STATUS_CLOSED) \
                       .exclude(sound=None) \
                       .order_by('status', '-created')
    pagination_response = paginate(request, qs, settings.MAX_TICKETS_IN_MODERATION_ASSIGNED_PAGE)
    pagination_response['page'].object_list = list(pagination_response['page'].object_list)
    # Because some tickets can have related sound which has disappeared or on deletion time the ticket
    # has not been properly updated, we need to check whether the sound that is related does in fact
    # exist. If it does not, we set the related sound to None and the status of the ticket to closed
    # as should have been set at sound deletion time.
    for ticket in pagination_response['page'].object_list:
        if not ticket.sound:
            pagination_response['page'].object_list.remove(ticket)
            ticket.status = TICKET_STATUS_CLOSED
            ticket.save()

    moderator_tickets_count = qs.count()
    moderation_texts = MODERATION_TEXTS
    show_pagination = moderator_tickets_count > settings.MAX_TICKETS_IN_MODERATION_ASSIGNED_PAGE

    tvars = {
            "moderator_tickets_count": moderator_tickets_count,
            "moderation_texts": moderation_texts,
            "page": pagination_response['page'],
            "paginator": pagination_response['paginator'],
            "current_page": pagination_response['current_page'],
            "show_pagination": show_pagination,
            "mod_sound_form": mod_sound_form,
            "msg_form": msg_form,
            "selected": "queue"
            }

    return render(request, 'tickets/moderation_assigned.html', tvars)


@permission_required('tickets.can_moderate')
@transaction.atomic()
def user_annotations(request, user_id):
    user = get_object_or_404(User, id=user_id)
    num_sounds_ok = Sound.objects.filter(user=user, moderation_state="OK").count()
    num_sounds_pending = Sound.objects.filter(user=user).exclude(moderation_state="OK").count()
    if request.method == 'POST':
        form = UserAnnotationForm(request.POST)
        if form.is_valid():
            ua = UserAnnotation(sender=request.user,
                                user=user,
                                text=form.cleaned_data['text'])
            ua.save()
    else:
        form = UserAnnotationForm()
    annotations = UserAnnotation.objects.filter(user=user)

    tvars = {"user": user,
             "num_sounds_ok": num_sounds_ok,
             "num_sounds_pending": num_sounds_pending,
             "form": form,
             "annotations": annotations}

    return render(request, 'tickets/user_annotations.html', tvars)


def get_pending_sounds(user):
    # gets all tickets from a user that have not been closed

    ret = []
    user_tickets = Ticket.objects.filter(sender=user).exclude(status=TICKET_STATUS_CLOSED)

    for user_ticket in user_tickets:
        sound = user_ticket.sound
        if sound.processing_state == 'OK' and sound.moderation_state == 'PE':
            ret.append( (user_ticket, sound) )

    return ret


@permission_required('tickets.can_moderate')
def pending_tickets_per_user(request, username):

    user = get_object_or_404(User, username=username)
    tickets_sounds = get_pending_sounds(user)
    pendings = []
    for ticket, sound in tickets_sounds:
        last_comments = ticket.get_n_last_non_moderator_only_comments(3)
        pendings.append( (ticket, sound, last_comments) )

    show_pagination = len(pendings) > settings.SOUNDS_PENDING_MODERATION_PER_PAGE

    n_unprocessed_sounds = Sound.objects.select_related().filter(user=user).exclude(processing_state="OK").count()
    if n_unprocessed_sounds:
        messages.add_message(request, messages.WARNING,
                             """%i of %s's recently uploaded sounds are still in processing
                             phase and therefore are not yet ready for moderation. These
                             sounds won't appear in this list until they are successfully
                             processed.""" % (n_unprocessed_sounds, user.username))

    moderators_version = True
    own_page = user == request.user

    paginated = paginate(request, pendings, settings.SOUNDS_PENDING_MODERATION_PER_PAGE)
    tvars = {"show_pagination": show_pagination,
             "moderators_version": moderators_version,
             "user": user,
             "own_page": own_page}
    tvars.update(paginated)

    return render(request, 'accounts/pending.html', tvars)
