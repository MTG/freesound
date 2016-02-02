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

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse
from models import Ticket, Queue, TicketComment
from forms import *
from tickets import *
from django.db import connection, transaction
from django.contrib import messages
from sounds.models import Sound
import datetime
from utils.cache import invalidate_template_cache
from utils.pagination import paginate
from utils.functional import combine_dicts
from django.core.management import call_command
from threading import Thread
from django.conf import settings
import gearman


def _get_contact_form(request, use_post=True):
    return _get_anon_or_user_form(request, AnonymousContactForm, UserContactForm, use_post)


def _get_tc_form(request, use_post=True):
    return _get_anon_or_user_form(request, AnonymousMessageForm, UserMessageForm, use_post)


def _get_anon_or_user_form(request, anonymous_form, user_form, use_post=True):
    if _can_view_mod_msg(request) and anonymous_form != AnonymousContactForm:
        user_form = ModeratorMessageForm
    if len(request.POST.keys()) > 0 and use_post:
        if request.user.is_authenticated():
            return user_form(request.POST)
        else:
            return anonymous_form(request, request.POST)
    else:
        return user_form() if request.user.is_authenticated() else anonymous_form(request)


def _can_view_mod_msg(request):
    return request.user.is_authenticated() \
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
    ticket = get_object_or_404(Ticket, key=ticket_key)
    if ticket.content:
        # Becuase it can happen that some tickets have linked content which has dissapeared or on deletion time the ticket
        # has not been propertly updated, we need to check whether the sound that is linked does in fact exist. If it does
        # not, we set the linked content to None and the status of the ticket to closed as should have been set at sound
        # deletion time.
        sound_id = ticket.content.object_id
        try:
            Sound.objects.get(id=sound_id)
        except Sound.DoesNotExist:
            ticket.content = None
            ticket.status = TICKET_STATUS_CLOSED
            ticket.save()

    if request.method == 'POST':

        invalidate_template_cache("user_header", ticket.sender.id)
        invalidate_all_moderators_header_cache()

        # Left ticket message
        if is_selected(request, 'recaptcha') or (request.user.is_authenticated() and is_selected(request, 'message')):
            tc_form = _get_tc_form(request)
            if tc_form.is_valid():
                tc = TicketComment()
                tc.text = tc_form.cleaned_data['message']
                tc.moderator_only = tc_form.cleaned_data.get('moderator_only', False)
                if tc.text:
                    if request.user.is_authenticated():
                        tc.sender = request.user
                    tc.ticket = ticket
                    tc.save()
                    if not request.user.is_authenticated():
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
                    if ticket.content:
                        ticket.content.content_object.delete()
                        ticket.content.delete()
                        ticket.content = None
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
                    if ticket.content:
                        ticket.content.content_object.moderation_state = sound_state
                        # Mark the index as dirty so it'll be indexed in Solr
                        if sound_state == "OK":
                            ticket.content.content_object.mark_index_dirty()
                        ticket.content.content_object.save()
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
        state = ticket.content.content_object.moderation_state if ticket.content else 'DE'
        sound_form = SoundStateForm(initial={'state': state}, prefix="ss")
    if clean_comment_form:
        tc_form = _get_tc_form(request, False)

    num_sounds_pending = Sound.objects.filter(user=ticket.sender).exclude(moderation_state="OK").count()
    tvars = {"ticket": ticket,
             "num_sounds_pending": num_sounds_pending,
             "tc_form": tc_form,
             "ticket_form": ticket_form,
             "sound_form": sound_form,
             "can_view_moderator_only_messages": can_view_moderator_only_messages}
    return render(request, 'tickets/ticket.html', tvars)


@login_required
def sound_ticket_messages(request, ticket_key):
    can_view_moderator_only_messages = _can_view_mod_msg(request)
    ticket = get_object_or_404(Ticket, key=ticket_key)
    tvars = {"can_view_moderator_only_messages": can_view_moderator_only_messages,
             "ticket": ticket}
    return render(request, 'tickets/message_list.html', tvars)


# In the next 2 functions we return a queryset os the evaluation is lazy.
# N.B. these functions are used in the home page as well.
def new_sound_tickets_count():
    return len(list(Ticket.objects.raw("""
        SELECT
        ticket.id
        FROM
        tickets_ticket AS ticket,
        sounds_sound AS sound,
        tickets_linkedcontent AS content
        WHERE
            ticket.content_id = content.id
        AND ticket.assignee_id is NULL
        AND content.object_id = sound.id
        AND sound.moderation_state = 'PE'
        AND sound.processing_state = 'OK'
        AND ticket.status = %s
        """, [TICKET_STATUS_NEW])))


def new_support_tickets_count():
    return Ticket.objects.filter(assignee=None,
                                 source=TICKET_SOURCE_CONTACT_FORM).count()


@permission_required('tickets.can_moderate')
def tickets_home(request):
    sounds_in_moderators_queue_count = _get_sounds_in_moderators_queue_count(request.user)

    new_upload_count = new_sound_tickets_count()
    tardy_moderator_sounds_count = len(list(_get_tardy_moderator_tickets()))
    tardy_user_sounds_count = len(list(_get_tardy_user_tickets()))
    sounds_queued_count = Sound.objects.filter(processing_ongoing_state='QU').count()
    sounds_pending_count = Sound.objects.filter(processing_state='PE').count()
    sounds_processing_count = Sound.objects.filter(processing_ongoing_state='PR').count()
    sounds_failed_count = Sound.objects.filter(processing_state='FA').count()

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
             "gearman_status": gearman_status,
             "sounds_in_moderators_queue_count": sounds_in_moderators_queue_count}

    return render(request, 'tickets/tickets_home.html', tvars)


def _get_new_uploaders_by_ticket():
    cursor = connection.cursor()
    cursor.execute("""
SELECT
    tickets_ticket.sender_id, count(*)
FROM
    tickets_ticket, tickets_linkedcontent, sounds_sound
WHERE
    tickets_ticket.source = 'new sound'
    AND sounds_sound.processing_state = 'OK'
    AND sounds_sound.moderation_state = 'PE'
    AND tickets_linkedcontent.object_id = sounds_sound.id
    AND tickets_ticket.content_id = tickets_linkedcontent.id
    AND tickets_ticket.assignee_id is NULL
    AND tickets_ticket.status = %s
GROUP BY sender_id""", [TICKET_STATUS_NEW])
    user_ids_plus_new_count = dict(cursor.fetchall())
    user_objects = User.objects.filter(id__in=user_ids_plus_new_count.keys())

    users_aux = []
    for user in user_objects:
        # Pick the oldest non moderated ticket of each user and compute how many seconds it has been in the queue
        user_new_tickets = Ticket.objects.filter(sender__id=user.id,
                                                 status=TICKET_STATUS_NEW,
                                                 content__isnull=False).order_by("created")
        if user_new_tickets:
            oldest_new_ticket_created = user_new_tickets[0].created
        else:
            oldest_new_ticket_created = datetime.datetime.now()

        for ticket in user_new_tickets:
            if ticket.content.content_object:
                content_object = ticket.content.content_object
                if content_object.processing_state == 'OK' and content_object.moderation_state == 'PE':
                    oldest_new_ticket_created = ticket.created

        days_in_queue = (datetime.datetime.now() - oldest_new_ticket_created).days
        users_aux.append({'user': user, 'days_in_queue': days_in_queue, 'new_sounds': user_ids_plus_new_count[user.id]})

    # Sort users according to their oldest ticket (older = first)
    users_aux.sort(key=lambda item: item['days_in_queue'], reverse=True)
    new_sounds_users = []
    for user in users_aux:
        new_sounds_users.append((user['user'],user['new_sounds'], user['days_in_queue']))

    return new_sounds_users


def _get_unsure_sound_tickets():
    """Query to get tickets that were returned to the queue by moderators that
    didn't know what to do with the sound."""
    return Ticket.objects.filter(source=TICKET_SOURCE_NEW_SOUND,
                                 assignee=None,
                                 status=TICKET_STATUS_ACCEPTED)


def _get_tardy_moderator_tickets(limit=None):
    """Get tickets for moderators that haven't responded in the last day"""
    query = """
        SELECT
        distinct(ticket.id),
        ticket.modified as modified
        FROM
        tickets_ticketcomment AS comment,
        tickets_ticket AS ticket
        WHERE comment.id in (   SELECT MAX(id)
                                FROM tickets_ticketcomment
                                GROUP BY ticket_id    )
        AND ticket.assignee_id is Not Null
        AND comment.ticket_id = ticket.id
        AND (comment.sender_id = ticket.sender_id OR comment.sender_id IS NULL)
        AND now() - modified > INTERVAL '24 hours'
        AND ticket.status != %s
        """
    if limit:
        query += " LIMIT %s" % (limit, )
    return Ticket.objects.raw(query, [TICKET_STATUS_CLOSED])


def _get_tardy_user_tickets(limit=None):
    """Get tickets for users that haven't responded in the last 2 days"""
    query = """
        SELECT
        distinct(ticket.id)
        FROM
        tickets_ticketcomment AS comment,
        tickets_ticket AS ticket
        WHERE comment.id in (   SELECT MAX(id)
                                FROM tickets_ticketcomment
                                GROUP BY ticket_id    )
        AND ticket.assignee_id is Not Null
        AND ticket.status != '%s'
        AND comment.ticket_id = ticket.id
        AND comment.sender_id != ticket.sender_id
        AND now() - comment.created > INTERVAL '2 days'
    """
    if limit:
        query += " LIMIT %s" % (limit, )
    return Ticket.objects.raw(query, [TICKET_STATUS_CLOSED])


def _get_sounds_in_moderators_queue_count(user):
    return Ticket.objects.select_related() \
        .filter(assignee=user.id) \
        .exclude(status='closed') \
        .exclude(content=None) \
        .order_by('status', '-created').count()


@permission_required('tickets.can_moderate')
def moderation_home(request):
    sounds_in_moderators_queue_count = _get_sounds_in_moderators_queue_count(request.user)

    new_sounds_users = _get_new_uploaders_by_ticket()
    unsure_tickets = list(_get_unsure_sound_tickets())  # TODO: shouldn't appear
    tardy_moderator_tickets = list(_get_tardy_moderator_tickets(5))
    tardy_user_tickets = list(_get_tardy_user_tickets(5))
    tardy_moderator_tickets_count = len(list(_get_tardy_moderator_tickets()))
    tardy_user_tickets_count = len(list(_get_tardy_user_tickets()))

    tvars = {"new_sounds_users": new_sounds_users,
             "unsure_tickets": unsure_tickets,
             "tardy_moderator_tickets": tardy_moderator_tickets,
             "tardy_user_tickets": tardy_user_tickets,
             "tardy_moderator_tickets_count": tardy_moderator_tickets_count,
             "tardy_user_tickets_count": tardy_user_tickets_count,
             "sounds_in_moderators_queue_count": sounds_in_moderators_queue_count}

    return render(request, 'tickets/moderation_home.html', tvars)


@permission_required('tickets.can_moderate')
def moderation_tardy_users_sounds(request):
    sounds_in_moderators_queue_count = _get_sounds_in_moderators_queue_count(request.user)
    tardy_user_tickets = list(_get_tardy_user_tickets())
    paginated = paginate(request, tardy_user_tickets, 10)

    tvars = {"sounds_in_moderators_queue_count": sounds_in_moderators_queue_count,
             "tardy_user_tickets": tardy_user_tickets}
    tvars.update(paginated)

    return render(request, 'tickets/moderation_tardy_users.html', tvars)


@permission_required('tickets.can_moderate')
def moderation_tardy_moderators_sounds(request):
    sounds_in_moderators_queue_count = _get_sounds_in_moderators_queue_count(request.user)
    tardy_moderators_tickets = list(_get_tardy_moderator_tickets())
    paginated = paginate(request, tardy_moderators_tickets, 10)

    tvars = {"sounds_in_moderators_queue_count": sounds_in_moderators_queue_count,
             "tardy_moderators_tickets": tardy_moderators_tickets}
    tvars.update(paginated)

    return render(request, 'tickets/moderation_tardy_moderators.html', tvars)


@permission_required('tickets.can_moderate')
def moderation_assign_user(request, user_id):
    sender = User.objects.get(id=user_id)
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE
            tickets_ticket
        SET
            assignee_id = %s,
            status = %s,
            modified = now()
        FROM
            sounds_sound,
            tickets_linkedcontent
        WHERE
            tickets_ticket.source = 'new sound'
        AND sounds_sound.processing_state = 'OK'
        AND sounds_sound.moderation_state = 'PE'
        AND tickets_linkedcontent.object_id = sounds_sound.id
        AND tickets_ticket.content_id = tickets_linkedcontent.id
        AND tickets_ticket.assignee_id is NULL
        AND tickets_ticket.status = %s
        AND sounds_sound.user_id = %s""",
            [request.user.id, TICKET_STATUS_ACCEPTED, TICKET_STATUS_NEW, sender.id])
    transaction.commit_unless_managed()
    msg = 'You have been assigned all new sounds from %s.' % sender.username
    messages.add_message(request, messages.INFO, msg)
    invalidate_all_moderators_header_cache()

    return redirect("tickets-moderation-home")


# TODO: ongoing work
@permission_required('tickets.can_moderate')
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
        else:
            return redirect(reverse("tickets-moderation-home")+"?page=%s" % p)
    else:
        return redirect("tickets-moderation-home")


@permission_required('tickets.can_moderate')
def moderation_assigned(request, user_id):
    
    can_view_moderator_only_messages = _can_view_mod_msg(request)
    clear_forms = True
    if request.method == 'POST':
        mod_sound_form = SoundModerationForm(request.POST)
        msg_form = ModerationMessageForm(request.POST)

        if mod_sound_form.is_valid() and msg_form.is_valid():

            ticket = Ticket.objects.get(id=mod_sound_form.cleaned_data.get("ticket", False))
            invalidate_template_cache("user_header", ticket.sender.id)
            invalidate_all_moderators_header_cache()
            action = mod_sound_form.cleaned_data.get("action")
            msg = msg_form.cleaned_data.get("message", False)
            moderator_only = msg_form.cleaned_data.get("moderator_only", False)

            if msg:
                tc = TicketComment(sender=ticket.assignee,
                                   text=msg,
                                   ticket=ticket,
                                   moderator_only=moderator_only)
                tc.save()

            if action == "Approve":
                ticket.status = TICKET_STATUS_CLOSED
                ticket.content.content_object.change_moderation_state("OK")  # change_moderation_state does the saving
                ticket.save()
                ticket.content.content_object.mark_index_dirty()
                if msg:
                    ticket.send_notification_emails(Ticket.NOTIFICATION_APPROVED_BUT,
                                                    Ticket.USER_ONLY)
                else:
                    ticket.send_notification_emails(Ticket.NOTIFICATION_APPROVED,
                                                    Ticket.USER_ONLY)
            elif action == "Defer":
                ticket.status = TICKET_STATUS_DEFERRED
                ticket.save()
                # only send a notification if a message was added
                if msg:
                    ticket.send_notification_emails(Ticket.NOTIFICATION_QUESTION,
                                                    Ticket.USER_ONLY)
            elif action == "Return":
                ticket.assignee = None
                ticket.status = TICKET_STATUS_NEW
                # no notification here
                ticket.save()
            elif action == "Delete":
                ticket.send_notification_emails(Ticket.NOTIFICATION_DELETED,
                                                Ticket.USER_ONLY)
                # to prevent a crash if the form is resubmitted
                if ticket.content:
                    ticket.content.content_object.delete()
                    ticket.content.delete()
                    ticket.content = None
                ticket.status = TICKET_STATUS_CLOSED
                ticket.save()
            elif action == "Whitelist":

                th = Thread(target=call_command, args=('whitelist_user', ticket.id,))
                th.start()
                ticket.send_notification_emails(Ticket.NOTIFICATION_WHITELISTED,
                                                Ticket.USER_ONLY)

                messages.add_message(request, messages.INFO,
                                     """User %s has been whitelisted but some of their tickets might
                                     still appear on this list for some time. Please reload the page in a few
                                     seconds to see the updated list of pending tickets""" % ticket.sender.username)

        else:
            clear_forms = False
    if clear_forms:
        mod_sound_form = SoundModerationForm(initial={'action': 'Approve'})
        msg_form = ModerationMessageForm()

    qs = Ticket.objects.select_related() \
                       .filter(assignee=user_id) \
                       .exclude(status=TICKET_STATUS_CLOSED) \
                       .exclude(content=None) \
                       .order_by('status', '-created')
    pagination_response = paginate(request, qs, settings.MAX_TICKETS_IN_MODERATION_ASSIGNED_PAGE)
    pagination_response['page'].object_list = list(pagination_response['page'].object_list)
    # Because some tickets can have linked content which has disappeared or on deletion time the ticket
    # has not been properly updated, we need to check whether the sound that is linked does in fact exist. If it does
    # not, we set the linked content to None and the status of the ticket to closed as should have been set at sound
    # deletion time.
    for ticket in pagination_response['page'].object_list:
        sound_id = ticket.content.object_id
        try:
            Sound.objects.get(id=sound_id)
        except Sound.DoesNotExist:
            pagination_response['page'].object_list.remove(ticket)
            ticket.content = None
            ticket.status = TICKET_STATUS_CLOSED
            ticket.save()

    moderator_tickets_count = qs.count()
    moderation_texts = MODERATION_TEXTS
    show_pagination = moderator_tickets_count > settings.MAX_TICKETS_IN_MODERATION_ASSIGNED_PAGE

    tvars = locals()
    tvars.update(pagination_response)

    return render(request, 'tickets/moderation_assigned.html', tvars)


@permission_required('tickets.can_moderate')
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
    ret = []
    # getting all user tickets that last that have not been closed
    user_tickets = Ticket.objects.filter(sender=user).exclude(status=TICKET_STATUS_CLOSED)

    for user_ticket in user_tickets:
        try:
            sound_id = user_ticket.content.object_id
            sound_obj = Sound.objects.get(id=sound_id, processing_state='OK', moderation_state='PE')
            ret.append( (user_ticket, sound_obj) )
        except:
            pass

    return ret


def get_num_pending_sounds(user):
    # Get non closed tickets with linked content objects referring to sounds that have not been deleted
    tickets = Ticket.objects.raw("""
                SELECT ticket.id
                  FROM tickets_ticket AS ticket
             LEFT JOIN tickets_linkedcontent AS content ON content.id = ticket.content_id
             LEFT JOIN sounds_sound AS sound ON sound.id=content.object_id
                 WHERE (ticket.sender_id = %s
                   AND NOT (ticket.status = 'closed' ))
                   AND sound.id IS NOT NULL
                   AND sound.moderation_state = 'PE'
                   AND sound.processing_state = 'OK'
    """, [user.id])
    return len(list(tickets))


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

    paginated = paginate(request, pendings, settings.SOUNDS_PENDING_MODERATION_PER_PAGE)
    tvars = {"show_pagination": show_pagination,
             "moderators_version": moderators_version,
             "user": user}
    tvars.update(paginated)

    return render(request, 'accounts/pending.html', tvars)


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='/')
def process_sounds(request, processing_status):

    sounds_to_process = None
    if processing_status == "FA":
        sounds_to_process = Sound.objects.filter(processing_state='FA')
    elif processing_status == "PE":
        sounds_to_process = Sound.objects.filter(processing_state='PE')

    # Remove sounds from the list that are already in the queue or are being processed right now
    if sounds_to_process:
        sounds_to_process = sounds_to_process.exclude(processing_ongoing_state='PR')\
            .exclude(processing_ongoing_state='QU')
        for sound in sounds_to_process:
            sound.process()

    return redirect("tickets-home")
