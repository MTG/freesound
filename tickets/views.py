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

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.db.models import Count, Min, Q, F
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from general.tasks import whitelist_user

from .models import Ticket, TicketComment, UserAnnotation
from sounds.models import Sound
from tickets import TICKET_STATUS_ACCEPTED, TICKET_STATUS_CLOSED, TICKET_STATUS_DEFERRED, TICKET_STATUS_NEW, MODERATION_TEXTS
from tickets.forms import AnonymousMessageForm, UserMessageForm, ModeratorMessageForm, AnonymousContactForm, \
    SoundStateForm, SoundModerationForm, ModerationMessageForm, UserAnnotationForm, IS_EXPLICIT_ADD_FLAG_KEY, IS_EXPLICIT_REMOVE_FLAG_KEY, IS_EXPLICIT_KEEP_USER_PREFERENCE_KEY
from utils.cache import invalidate_user_template_caches
from utils.frontend_handling import render, using_beastwhoosh
from utils.username import redirect_if_old_username_or_404
from utils.pagination import paginate
from wiki.models import Content, Page


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
        invalidate_user_template_caches(mod.id)


def ticket(request, ticket_key):
    can_view_moderator_only_messages = _can_view_mod_msg(request)
    clean_status_forms = True
    clean_comment_form = True
    ticket = get_object_or_404(Ticket.objects.select_related('sound__license', 'sound__user'), key=ticket_key)

    if request.method == 'POST':

        invalidate_user_template_caches(ticket.sender.id)
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
        elif is_selected(request, 'ss'):
            sound_form = SoundStateForm(request.POST, prefix='ss')
            if sound_form.is_valid():
                clean_status_forms = True
                clean_comment_form = True
                sound_action = sound_form.cleaned_data.get('action')
                comment = f'Moderator {request.user} '
                notification = None

                # If there is no one assigned, then changing the state self-assigns the ticket
                if ticket.assignee is None:
                    ticket.assignee = request.user

                if sound_action == 'Delete':
                    if ticket.sound:
                        ticket.sound.delete()
                        ticket.sound = None
                    ticket.status = TICKET_STATUS_CLOSED
                    comment += 'deleted the sound and closed the ticket'
                    notification = ticket.NOTIFICATION_DELETED

                elif sound_action == 'Defer':
                    ticket.status = TICKET_STATUS_DEFERRED
                    ticket.sound.change_moderation_state('PE')  # not sure if this state have been used before
                    comment += 'deferred the ticket'

                elif sound_action == "Return":
                    ticket.status = TICKET_STATUS_NEW
                    ticket.assignee = None
                    ticket.sound.change_moderation_state('PE')
                    comment += 'returned the ticket to new sounds queue'

                elif sound_action == 'Approve':
                    ticket.status = TICKET_STATUS_CLOSED
                    ticket.sound.change_moderation_state('OK')
                    comment += 'approved the sound and closed the ticket'
                    notification = ticket.NOTIFICATION_APPROVED

                elif sound_action == 'Whitelist':
                    whitelist_user.delay(ticket_ids=[ticket.id])  # async job should take care of whitelisting
                    comment += f'whitelisted all sounds from user {ticket.sender}'
                    notification = ticket.NOTIFICATION_WHITELISTED

                if notification is not None:
                    ticket.send_notification_emails(notification,
                                                    ticket.USER_ONLY)

                if ticket.sound is not None:
                    ticket.sound.save()

                ticket.save()
                tc = TicketComment(sender=request.user,
                                   text=comment,
                                   ticket=ticket,
                                   moderator_only=False)
                tc.save()

    if clean_status_forms:
        default_action = 'Return' if ticket.sound and ticket.sound.moderation_state == 'OK' else 'Approve'
        sound_form = SoundStateForm(initial={'action': default_action}, prefix="ss")
    if clean_comment_form:
        tc_form = _get_tc_form(request, False)

    num_sounds_pending = ticket.sender.profile.num_sounds_pending_moderation()
    tvars = {"ticket": ticket,
             "num_sounds_pending": num_sounds_pending,
             "tc_form": tc_form,
             "sound_form": sound_form,
             "can_view_moderator_only_messages": can_view_moderator_only_messages}
    return render(request, 'tickets/ticket.html', tvars)


# In the next 2 functions we return a queryset os the evaluation is lazy.
# N.B. these functions are used in the home page as well.
def new_sound_tickets_count():
    return len(Ticket.objects.filter(assignee=None,
                                     sound__moderation_state='PE',
                                     sound__processing_state='OK',
                                     status=TICKET_STATUS_NEW))

@login_required
def sound_ticket_messages(request, ticket_key):
    can_view_moderator_only_messages = _can_view_mod_msg(request)
    ticket = get_object_or_404(Ticket, key=ticket_key)
    tvars = {"can_view_moderator_only_messages": can_view_moderator_only_messages,
             "ticket": ticket}
    return render(request, 'tickets/message_list.html', tvars)


def _get_new_uploaders_by_ticket():

    tickets = Ticket.objects.filter(assignee=None,
                                    sound__processing_state='OK',
                                    sound__moderation_state='PE',
                                    status=TICKET_STATUS_NEW)\
        .values('sender')\
        .annotate(total=Count('sender'), older=Min('created'))\
        .order_by('older')

    users = User.objects.filter(id__in=[t['sender'] for t in tickets]).select_related('profile')
    users_dict = {u.id: u for u in users}
    new_sounds_users = []

    for t in tickets:
        new_sounds_users.append({"user": users_dict[t['sender']],
                                 "username": users_dict[t['sender']].username,
                                 "new_count": t['total'],
                                 "time": (datetime.datetime.now() - t['older']).days})
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
def assign_sounds(request):
    sounds_in_moderators_queue_count = _get_sounds_in_moderators_queue_count(request.user)

    unsure_tickets = _get_unsure_sound_tickets()
    new_sounds_users = _get_new_uploaders_by_ticket()
    order = request.GET.get("order", "")
    if order == "username":
        new_sounds_users = sorted(new_sounds_users, key=lambda x: x["username"])
    elif order == "new_count":
        new_sounds_users = sorted(new_sounds_users, key=lambda x: x["new_count"], reverse=True)
    else:
        # Default option, sort by number of days in queue
        new_sounds_users = sorted(new_sounds_users, key=lambda x: x["time"], reverse=True)

    tardy_moderator_tickets = _get_tardy_moderator_tickets()
    tardy_user_tickets = _get_tardy_user_tickets()
    tardy_moderator_tickets_count = len(tardy_moderator_tickets)
    tardy_user_tickets_count = len(tardy_user_tickets)

    tvars = {"new_sounds_users": new_sounds_users,
             "order": order,
             "unsure_tickets": unsure_tickets,
             "tardy_moderator_tickets": tardy_moderator_tickets[:5],
             "tardy_user_tickets": tardy_user_tickets[:5],
             "tardy_moderator_tickets_count": tardy_moderator_tickets_count,
             "tardy_user_tickets_count": tardy_user_tickets_count,
             "moderator_tickets_count": sounds_in_moderators_queue_count
            }

    if using_beastwhoosh(request):
        tvars.update({'section': 'assign'})
        return render(request, 'moderation/assign_sounds.html', tvars)    
    else:
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
def moderation_assign_all_new(request):
    """
    Assigns all new unassigned tickets to the current user logged in
    """

    tickets = Ticket.objects.filter(assignee=None,
                                    sound__processing_state='OK',
                                    sound__moderation_state='PE',
                                    status=TICKET_STATUS_NEW)

    tickets.update(assignee=request.user, status=TICKET_STATUS_ACCEPTED, modified=datetime.datetime.now())

    msg = f'You have been assigned all new sounds ({tickets.count()}) from the queue.'
    messages.add_message(request, messages.INFO, msg)
    invalidate_all_moderators_header_cache()

    return redirect("tickets-moderation-home")


@permission_required('tickets.can_moderate')
def moderation_assign_user(request, user_id, only_unassigned=True):
    """
    With only_unassigned set to True this function will assign only sounds that have no assignee.
    Otherwise it will target all pending sounds from that user.
    """
    sender = User.objects.get(id=user_id)

    tickets = Ticket.objects.filter(sound__processing_state='OK', sound__moderation_state='PE', sound__user=sender)\
        .exclude(status=TICKET_STATUS_CLOSED)

    if only_unassigned:
        tickets = tickets.filter(assignee=None, status=TICKET_STATUS_NEW)

    tickets.update(assignee=request.user, status=TICKET_STATUS_ACCEPTED, modified=datetime.datetime.now())

    msg = f'You have been assigned all new sounds from {sender.username}.'
    messages.add_message(request, messages.INFO, msg)
    invalidate_all_moderators_header_cache()

    return redirect("tickets-moderation-home")


@permission_required('tickets.can_moderate')
def moderation_assign_user_pending(request, user_id):
    return moderation_assign_user(request, user_id, only_unassigned=False)


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

    msg = f'You have been assigned ticket "{ticket.title}".'
    messages.add_message(request, messages.INFO, msg)

    next = request.GET.get("next", None)
    p = request.GET.get("p", 1)

    if next:
        if next == "tardy_users":
            return redirect("tickets-moderation-tardy-users")
        elif next == "tardy_moderators":
            return redirect(reverse("tickets-moderation-tardy-moderators")+f"?page={p}")
        elif next == "ticket":
            return redirect(reverse("tickets-ticket", kwargs={'ticket_key': ticket.key}))
        else:
            return redirect(reverse("tickets-moderation-home")+f"?page={p}")
    else:
        return redirect("tickets-moderation-home")


@permission_required('tickets.can_moderate')
@transaction.atomic()
def moderation_assigned(request, user_id):

    clear_forms = True
    mod_sound_form = None
    msg_form = None
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
                sounds_update_params = {
                    'is_index_dirty': True,
                    'moderation_state': 'OK',
                    'moderation_date': datetime.datetime.now()
                }
                is_explicit_choice_key = mod_sound_form.cleaned_data.get("is_explicit")
                if is_explicit_choice_key == IS_EXPLICIT_ADD_FLAG_KEY:
                    sounds_update_params['is_explicit'] = True
                elif is_explicit_choice_key == IS_EXPLICIT_REMOVE_FLAG_KEY:
                    sounds_update_params['is_explicit'] = False

                # Otherwise is_explicit_choice_key = IS_EXPLICIT_KEEP_USER_PREFERENCE_KEY, don't update the
                # 'is_explicit' field and leave it as the user originally set it

                Sound.objects.filter(ticket__in=tickets).update(**sounds_update_params)

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
                whitelist_user.delay(ticket_ids=ticket_ids)  # async job should take care of whitelisting
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
                invalidate_user_template_caches(ticket.sender.id)
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

    qs = Ticket.objects.select_related('sound') \
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
    show_pagination = moderator_tickets_count > settings.MAX_TICKETS_IN_MODERATION_ASSIGNED_PAGE

    tvars = {
        "moderator_tickets_count": moderator_tickets_count,
        "moderation_texts": MODERATION_TEXTS,
        "page": pagination_response['page'],
        "paginator": pagination_response['paginator'],
        "current_page": pagination_response['current_page'],
        "show_pagination": show_pagination,
        "max_selected_tickets_in_right_panel": settings.MAX_TICKETS_IN_MODERATION_ASSIGNED_PAGE_SELECTED_COLUMN,
        "mod_sound_form": mod_sound_form,
        "msg_form": msg_form,
        "default_autoplay": request.GET.get('autoplay', 'on') == 'on',
        "default_include_deferred": request.GET.get('include_d', '') == 'on',
    }

    if using_beastwhoosh(request):
        tvars.update({'section': 'assigned'})
        return render(request, 'moderation/assigned.html', tvars)
    else:
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
    # gets all tickets from a user that have not been closed (and that have an assigned sound)
    ret = []
    user_tickets = Ticket.objects.filter(sender=user).exclude(status=TICKET_STATUS_CLOSED).exclude(sound=None).order_by('-assignee')
    for user_ticket in user_tickets:
        sound = user_ticket.sound
        if sound.processing_state == 'OK' and sound.moderation_state == 'PE':
            ret.append( (user_ticket, sound) )
    return ret


@permission_required('tickets.can_moderate')
@redirect_if_old_username_or_404
def pending_tickets_per_user(request, username):
    user = request.parameter_user
    tickets_sounds = get_pending_sounds(user)
    pendings = []
    mods = set()
    for ticket, sound in tickets_sounds:
        last_comments = ticket.get_n_last_non_moderator_only_comments(3)
        pendings.append( (ticket, sound, last_comments) )
        mods.add(ticket.assignee)

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
    no_assign_button = len(mods) == 0 or (len(mods) == 1 and request.user in mods)

    paginated = paginate(request, pendings, settings.SOUNDS_PENDING_MODERATION_PER_PAGE)
    tvars = {"show_pagination": show_pagination,
             "moderators_version": moderators_version,
             "user": user,
             "own_page": own_page,
             "no_assign_button": no_assign_button}
    tvars.update(paginated)

    return render(request, 'accounts/pending.html', tvars)


@permission_required('tickets.can_moderate')
def guide(request):
    name = "moderators_bw"
    page = Page.objects.get(name__iexact=name)
    content = Content.objects.select_related().filter(page=page).latest()
    tvars = {'content': content,
             'name': name,
             'section': 'guide'}
    return render(request, 'moderation/guide.html', tvars)