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
from django.db.models import Count, Min, Q, F, OuterRef
from django.db.models.functions import JSONObject
from django.http import HttpResponseRedirect, JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from general.tasks import whitelist_user as whitelist_user_task

from .models import Ticket, TicketComment, UserAnnotation
from sounds.models import Sound
from tickets import TICKET_STATUS_ACCEPTED, TICKET_STATUS_CLOSED, TICKET_STATUS_DEFERRED, TICKET_STATUS_NEW, MODERATION_TEXTS
from tickets.forms import AnonymousMessageForm, BWAnonymousMessageForm, UserMessageForm, BWUserMessageForm, ModeratorMessageForm, BWModeratorMessageForm, \
    SoundStateForm, SoundModerationForm, ModerationMessageForm, UserAnnotationForm, IS_EXPLICIT_ADD_FLAG_KEY, IS_EXPLICIT_REMOVE_FLAG_KEY, \
    BWSoundModerationForm, BWModerationMessageForm
from utils.cache import invalidate_user_template_caches, invalidate_all_moderators_header_cache
from utils.frontend_handling import render, using_beastwhoosh
from utils.username import redirect_if_old_username_or_404
from utils.pagination import paginate
from wiki.models import Content, Page


def _get_tc_form(request, use_post=True):
    return _get_anon_or_user_form(request, 
                                  BWAnonymousMessageForm if using_beastwhoosh(request) else AnonymousMessageForm, 
                                  BWUserMessageForm if using_beastwhoosh(request) else UserMessageForm, 
                                  use_post)


def _get_anon_or_user_form(request, anonymous_form, user_form, use_post=True):
    if _can_view_mod_msg(request):
        user_form = BWModeratorMessageForm if using_beastwhoosh(request) else ModeratorMessageForm
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


@login_required
def ticket(request, ticket_key):
    can_view_moderator_only_messages = _can_view_mod_msg(request)
    clean_status_forms = True
    clean_comment_form = True
    ticket = get_object_or_404(Ticket.objects.select_related('sound__license', 'sound__user'), key=ticket_key)

    if not (ticket.sender == request.user or _can_view_mod_msg(request)):
        raise Http404

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

            if ticket.sound is None:
                # If ticket has not sound associated, we allow an extra option to close the ticket
                # Even if the options will not be displayed to the user, we need this extra option so the form
                # validates properly when the hardcoded "Close" option is used
                sound_form.fields['action'].choices += (('Close', 'Close'),)

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
                    whitelist_user_task.delay(ticket_ids=[ticket.id])  # async job should take care of whitelisting
                    comment += f'whitelisted all sounds from user {ticket.sender}'
                    notification = ticket.NOTIFICATION_WHITELISTED

                elif sound_action == 'Close':
                    # This option in never shown in the form, but used when needing to close a ticket which has no sound associated (see ticket.html)
                    ticket.status = TICKET_STATUS_CLOSED
                    comment = None  # Avoid adding a comment to the ticket

                if notification is not None:
                    ticket.send_notification_emails(notification,
                                                    ticket.USER_ONLY)

                if ticket.sound is not None:
                    ticket.sound.save()
                
                ticket.save()
                if comment is not None:
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

    tvars = {"ticket": ticket,
             "tc_form": tc_form,
             "sound_form": sound_form,
             "can_view_moderator_only_messages": can_view_moderator_only_messages,
             "num_sounds_pending": ticket.sender.profile.num_sounds_pending_moderation()
    }
    if using_beastwhoosh(request):
        sound_object = Sound.objects.bulk_query_id(sound_ids=[ticket.sound_id])[0] if ticket.sound_id is not None else None
        if sound_object is not None:
            sound_object.show_processing_status = True
            sound_object.show_moderation_status = True
        tvars.update({
            'sound': sound_object
        })
        return render(request, 'moderation/ticket.html', tvars)
    else:
        return render(request, 'tickets/ticket.html', tvars)


# In the next 2 functions we return a queryset os the evaluation is lazy.
# N.B. these functions are used in the home page as well.
def new_sound_tickets_count():
    return Ticket.objects.filter(
        assignee=None,
        sound__moderation_state='PE',
        sound__processing_state='OK',
        status=TICKET_STATUS_NEW).count()


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
                                 "num_uploaded_sounds": users_dict[t['sender']].profile.num_sounds,
                                 "time": (datetime.datetime.now() - t['older']).days})
    return new_sounds_users


def _annotate_tickets_queryset_with_message_info(qs, include_mod_messages=True):
    if include_mod_messages:
        return qs.select_related('assignee', 'sender').annotate(
            num_messages=Count('messages'),
            last_message=TicketComment.objects.filter(ticket_id=OuterRef('id')).select_related('sender').order_by('-created').values(
            data=JSONObject(text="text", sender_username='sender__username'))[:1])
    else:
        return qs.select_related('assignee', 'sender').annotate(
            num_messages=Count('messages', filter=Q(messages__moderator_only=False)),
            last_message=TicketComment.objects.filter(ticket_id=OuterRef('id'), moderator_only=False).select_related('sender').order_by('-created').values(
            data=JSONObject(text="text", sender_username='sender__username'))[:1])
    

def _add_sound_objects_to_tickets(tickets):
    sound_objects = Sound.objects.dict_ids(sound_ids=[ticket.sound_id for ticket in tickets])
    for ticket in tickets:
        ticket.sound_obj = sound_objects.get(ticket.sound_id, None)


def _get_unsure_sound_tickets_and_count(num=None, include_mod_messages=True):
    """Query to get tickets that were returned to the queue by moderators that
    didn't know what to do with the sound."""
    # NOTE: I don't think we are using this anymore as returned tickets will appear in the main unassigned queue (?)
    tt = Ticket.objects.filter(
        assignee=None,
        status=TICKET_STATUS_ACCEPTED
    )
    count = tt.count()
    return _annotate_tickets_queryset_with_message_info(tt[:num], include_mod_messages=include_mod_messages), count


def _get_tardy_moderator_tickets_and_count(num=None, include_mod_messages=True):
    """Get tickets for moderators that haven't responded in the last day"""
    time_span = datetime.date.today() - datetime.timedelta(days=1)
    tt = Ticket.objects\
    .filter(
        Q(assignee__isnull=False) &
        ~Q(status=TICKET_STATUS_CLOSED) &
        (Q(last_commenter=F('sender')) | Q(messages__sender=None)) &
        Q(comment_date__lt=time_span))
    count = tt.count()
    return _annotate_tickets_queryset_with_message_info(tt[:num], include_mod_messages=include_mod_messages), count


def _get_tardy_user_tickets_and_count(num=None, include_mod_messages=True):
    """Get tickets for users that haven't responded in the last 2 days"""
    time_span = datetime.date.today() - datetime.timedelta(days=2)
    tt = Ticket.objects\
    .filter(
        Q(assignee__isnull=False) &
        ~Q(status=TICKET_STATUS_CLOSED) &
        ~Q(last_commenter=F('sender')) &
        Q(comment_date__lt=time_span))
    count = tt.count()
    return _annotate_tickets_queryset_with_message_info(tt[:num], include_mod_messages=include_mod_messages), count


def _get_pending_tickets_for_user_base_qs(user):
    return Ticket.objects\
        .filter(sender=user)\
        .exclude(status=TICKET_STATUS_CLOSED)\
        .exclude(sound=None)\
        .filter(sound__processing_state='OK')\
        .exclude(sound__moderation_state='OK')


def _get_pending_tickets_for_user(user, include_mod_messages=True):
    # gets all tickets from a user that have not been closed (and that have an assigned sound)
    tt = _get_pending_tickets_for_user_base_qs(user).order_by('-assignee')
    count = tt.count()
    return _annotate_tickets_queryset_with_message_info(tt, include_mod_messages=include_mod_messages), count


def _get_sounds_in_moderators_queue_count(user):
    return Ticket.objects.select_related() \
        .filter(assignee=user.id) \
        .exclude(status='closed') \
        .exclude(sound=None) \
        .order_by('status', '-created').count()


@permission_required('tickets.can_moderate')
def assign_sounds(request):
    sounds_in_moderators_queue_count = _get_sounds_in_moderators_queue_count(request.user)

    new_sounds_users = _get_new_uploaders_by_ticket()
    num_sounds_pending = sum([u['new_count'] for u in new_sounds_users])
    order = request.GET.get("order", "")
    if order == "username":
        new_sounds_users = sorted(new_sounds_users, key=lambda x: x["username"])
    elif order == "new_count":
        new_sounds_users = sorted(new_sounds_users, key=lambda x: x["new_count"], reverse=True)
    elif order == "num_uploaded_sounds":
        new_sounds_users = sorted(new_sounds_users, key=lambda x: x["num_uploaded_sounds"], reverse=True)
    else:
        # Default option, sort by number of days in queue
        new_sounds_users = sorted(new_sounds_users, key=lambda x: x["time"], reverse=True)

    tardy_moderator_tickets, tardy_moderator_tickets_count = _get_tardy_moderator_tickets_and_count(num=8, include_mod_messages=True)
    tardy_user_tickets, tardy_user_tickets_count = _get_tardy_user_tickets_and_count(num=8, include_mod_messages=True)

    tvars = {"new_sounds_users": new_sounds_users,
             "num_sounds_pending": num_sounds_pending,
             "order": order,
             "tardy_moderator_tickets": tardy_moderator_tickets,
             "tardy_user_tickets": tardy_user_tickets,
             "tardy_moderator_tickets_count": tardy_moderator_tickets_count,
             "tardy_user_tickets_count": tardy_user_tickets_count,
             "moderator_tickets_count": sounds_in_moderators_queue_count
            }

    if using_beastwhoosh(request):
        _add_sound_objects_to_tickets(tardy_moderator_tickets)
        _add_sound_objects_to_tickets(tardy_user_tickets)
        tvars.update({'section': 'assign'})
        return render(request, 'moderation/assign_sounds.html', tvars)    
    else:
        return render(request, 'tickets/moderation_home.html', tvars)


@permission_required('tickets.can_moderate')
def moderation_tardy_users_sounds(request):
    if using_beastwhoosh(request) and not request.GET.get('ajax'):
        return HttpResponseRedirect(reverse('tickets-moderation-home') + '?tardy_users=1')
    
    sounds_in_moderators_queue_count = _get_sounds_in_moderators_queue_count(request.user)
    tardy_user_tickets, _ = _get_tardy_user_tickets_and_count(include_mod_messages=True)
    paginated = paginate(request, tardy_user_tickets, settings.SOUNDS_PENDING_MODERATION_PER_PAGE)

    tvars = {"moderator_tickets_count": sounds_in_moderators_queue_count,
             "tardy_user_tickets": tardy_user_tickets,
             "selected": "assigned"}
    tvars.update(paginated)

    if using_beastwhoosh(request):
        # Retrieve sound objects using bulk stuff so extra sound information is retrieved in one query
        _add_sound_objects_to_tickets(tvars['page'].object_list)
        tvars.update({'type': 'tardy_users'})
        return render(request, 'moderation/modal_tardy.html', tvars)
    else:
        return render(request, 'tickets/moderation_tardy_users.html', tvars)


@permission_required('tickets.can_moderate')
def moderation_tardy_moderators_sounds(request):
    if using_beastwhoosh(request) and not request.GET.get('ajax'):
        return HttpResponseRedirect(reverse('tickets-moderation-home') + '?tardy_moderators=1')
    
    sounds_in_moderators_queue_count = _get_sounds_in_moderators_queue_count(request.user)
    tardy_moderators_tickets, _ = _get_tardy_moderator_tickets_and_count(include_mod_messages=True)
    paginated = paginate(request, tardy_moderators_tickets, settings.SOUNDS_PENDING_MODERATION_PER_PAGE)

    tvars = {"moderator_tickets_count": sounds_in_moderators_queue_count,
             "tardy_moderators_tickets": tardy_moderators_tickets,
             "selected": "assigned"}
    tvars.update(paginated)

    if using_beastwhoosh(request):
        # Retrieve sound objects using bulk stuff so extra sound information is retrieved in one query
        _add_sound_objects_to_tickets(tvars['page'].object_list)
        tvars.update({'type': 'tardy_moderators'})
        return render(request, 'moderation/modal_tardy.html', tvars)
    else:
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
def moderation_assign_single_ticket(request, ticket_id):
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
    # TODO: once removing NG code, this view can be simplified as the msg form is now handled in the annotations modal
    clear_forms = True
    mod_sound_form = None
    msg_form = None
    SoundModerationFormClass = SoundModerationForm if not using_beastwhoosh(request) else BWSoundModerationForm
    ModerationMessageFormClass = ModerationMessageForm if not using_beastwhoosh(request) else BWModerationMessageForm
    if request.method == 'POST':
        mod_sound_form = SoundModerationFormClass(request.POST)
        msg_form = ModerationMessageFormClass(request.POST)

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
                whitelist_user_task.delay(ticket_ids=ticket_ids)  # async job should take care of whitelisting
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

            messages.add_message(request, messages.INFO, f"{len(tickets)} ticket(s) successfully updated")
        else:
            clear_forms = False
    if clear_forms:
        mod_sound_form = SoundModerationFormClass(initial={'action': 'Approve'})
        msg_form = ModerationMessageFormClass()

    qs = Ticket.objects.select_related('sound', 'sender') \
                       .filter(assignee=user_id) \
                       .exclude(status=TICKET_STATUS_CLOSED) \
                       .exclude(sound=None) \
                       .order_by('status', '-created')
    page_size = settings.MAX_TICKETS_IN_MODERATION_ASSIGNED_PAGE_BW if using_beastwhoosh(request) else settings.MAX_TICKETS_IN_MODERATION_ASSIGNED_PAGE
    pagination_response = paginate(request, qs, page_size)
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
    show_pagination = moderator_tickets_count > page_size

    tvars = {
        "moderator_tickets_count": moderator_tickets_count,
        "moderation_texts": MODERATION_TEXTS,
        "page": pagination_response['page'],
        "paginator": pagination_response['paginator'],
        "current_page": pagination_response['current_page'],
        "show_pagination": show_pagination,
        "max_selected_tickets_in_right_panel": settings.MAX_TICKETS_IN_MODERATION_ASSIGNED_PAGE_SELECTED_COLUMN,  # Not used in BW
        "mod_sound_form": mod_sound_form,
        "msg_form": msg_form,
        "default_autoplay": request.GET.get('autoplay', 'on') == 'on',
        "default_include_deferred": request.GET.get('include_d', '') == 'on',
    }

    if using_beastwhoosh(request):
        _add_sound_objects_to_tickets(tvars['page'].object_list)
        tvars.update({'section': 'assigned'})
        return render(request, 'moderation/assigned.html', tvars)
    else:
        return render(request, 'tickets/moderation_assigned.html', tvars)


@permission_required('tickets.can_moderate')
@transaction.atomic()
def user_annotations(request, user_id):
    user = get_object_or_404(User.objects.select_related('profile'), id=user_id)
    if using_beastwhoosh(request) and not request.GET.get('ajax'):
        return HttpResponseRedirect(reverse('account', args=[user.username]) + '?mod_annotations=1')
    annotations = UserAnnotation.objects.filter(user=user)
    if using_beastwhoosh(request):
        user_recent_ticket_comments = TicketComment.objects.filter(sender=user).select_related('ticket').order_by('-created')[:15]
        tvars = {"user": user,
                 "recent_comments": user_recent_ticket_comments,
                 "form": UserAnnotationForm(),
                 "annotations": annotations}
        return render(request, 'moderation/modal_annotations.html', tvars)
    else:
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


@permission_required('tickets.can_moderate')
@transaction.atomic()
def add_user_annotation(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = UserAnnotationForm(request.POST)
        if form.is_valid():
            ua = UserAnnotation(sender=request.user,
                                user=user,
                                text=form.cleaned_data['text'])
            ua.save()
            return JsonResponse({'message': 'Annotation successfully added', 'num_annotations': UserAnnotation.objects.filter(user=user).count()})
    return JsonResponse({'message': 'Annotation could not be added', 'num_annotations': UserAnnotation.objects.filter(user=user).count()})


@permission_required('tickets.can_moderate')
@redirect_if_old_username_or_404
def pending_tickets_per_user(request, username):
    if using_beastwhoosh(request) and not request.GET.get('ajax'):
        return HttpResponseRedirect(reverse('account', args=[username]) + '?pending_moderation=1')
    
    user = request.parameter_user
    tickets, _ = _get_pending_tickets_for_user(user, include_mod_messages=True)
    _add_sound_objects_to_tickets(tickets)
    mods = set()
    for ticket in tickets:
        mods.add(ticket.assignee)
    show_pagination = len(tickets) > settings.SOUNDS_PENDING_MODERATION_PER_PAGE
    
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

    paginated = paginate(request, tickets, settings.SOUNDS_PENDING_MODERATION_PER_PAGE)
    tvars = {"show_pagination": show_pagination,
             "moderators_version": moderators_version,
             "user": user,
             "own_page": own_page,
             "no_assign_button": no_assign_button}
    tvars.update(paginated)

    if using_beastwhoosh(request):
        return render(request, 'moderation/modal_pending.html', tvars)
    else:
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


@permission_required('tickets.can_moderate')
def whitelist_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except (User.DoesNotExist, AttributeError):
        messages.add_message(request, messages.ERROR,
                             """The user you are trying to whitelist does not exist""")
        return HttpResponseRedirect(reverse('tickets-moderation-home'))
    
    whitelist_user_task(user_id=user_id)  # async job should take care of whitelisting
    
    messages.add_message(request, messages.INFO,
        f"""User {user.username} has been whitelisted. Note that some of tickets might
        still appear on her pending tickets list for some time.""")

    redirect_to = request.GET.get('next', None)
    if redirect_to is not None:
        return HttpResponseRedirect(redirect_to)

    return HttpResponseRedirect('tickets-moderation-home')
