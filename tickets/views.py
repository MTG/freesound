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

from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from models import Ticket, Queue, TicketComment
from forms import *
from tickets import *
from django.db import connection, transaction
from django.contrib import messages
from sounds.models import Sound
import datetime
from utils.pagination import paginate
from utils.functional import combine_dicts


def __get_contact_form(request, use_post=True):
    return __get_anon_or_user_form(request, AnonymousContactForm, UserContactForm, use_post)


def __get_tc_form(request, use_post=True):
    return __get_anon_or_user_form(request, AnonymousMessageForm, UserMessageForm, use_post, True)


def __get_anon_or_user_form(request, anonymous_form, user_form, use_post=True, include_mod=False):
    if __can_view_mod_msg(request) and anonymous_form != AnonymousContactForm:
        user_form = ModeratorMessageForm
    if len(request.POST.keys()) > 0 and use_post:
        if request.user.is_authenticated():
            return user_form(request.POST)
        else:
            return anonymous_form(request, request.POST)
    else:
        return user_form() if request.user.is_authenticated() else anonymous_form(request)

def __can_view_mod_msg(request):
    return request.user.is_authenticated() \
            and (request.user.is_superuser or request.user.is_staff \
                 or Group.objects.get(name='moderators') in request.user.groups.all())

# TODO: copied from sound_edit view,
def is_selected(request, prefix):
    for name in request.POST.keys():
        if name.startswith(prefix):
            return True
    return False

def ticket(request, ticket_key):
    can_view_moderator_only_messages = __can_view_mod_msg(request)
    clean_status_forms = True
    clean_comment_form = True
    ticket = get_object_or_404(Ticket, key=ticket_key)
    if request.method == 'POST':
        # Left ticket message
        if is_selected(request, 'recaptcha') or (request.user.is_authenticated() and is_selected(request, 'message')):
            tc_form = __get_tc_form(request)
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
                                       text="Moderator %s set the sound to %s and the ticket to %s." % \
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
        sound_form = SoundStateForm(initial={'state':
                                             ticket.content.content_object.moderation_state \
                                             if ticket.content else 'DE'},
                                             prefix="ss")
    if clean_comment_form:
        tc_form = __get_tc_form(request, False)
    return render_to_response('tickets/ticket.html',
                              locals(),
                              context_instance=RequestContext(request))


@login_required
def sound_ticket_messages(request, ticket_key):
    can_view_moderator_only_messages = __can_view_mod_msg(request)
    ticket = get_object_or_404(Ticket, key=ticket_key)
    return render_to_response('tickets/message_list.html',
                              locals(),
                              context_instance=RequestContext(request))


def new_contact_ticket(request):
    ticket_created = False
    if request.POST:
        form = __get_contact_form(request)
        if form.is_valid():
            ticket = Ticket()
            ticket.title = form.cleaned_data['title']
            ticket.source = TICKET_SOURCE_CONTACT_FORM
            ticket.status = TICKET_STATUS_NEW
            ticket.queue = Queue.objects.get(name=QUEUE_SUPPORT_REQUESTS)
            tc = TicketComment()
            if request.user.is_authenticated():
                ticket.sender = request.user
                tc.sender = request.user
            else:
                ticket.sender_email = form.cleaned_data['email']
            tc.text = form.cleaned_data['message']
            ticket.save()
            tc.ticket = ticket
            tc.save()
            ticket_created = True
            # TODO: send email
    else:
        form = __get_contact_form(request, False)
    return render_to_response('tickets/contact.html', locals(), context_instance=RequestContext(request))


# In the next 2 functions we return a queryset os the evaluation is lazy.
# N.B. these functions are used in the home page as well.
def new_sound_tickets_count():
#AND (sound.processing_state = 'OK' OR sound.processing_state = 'FA')
#    return Ticket.objects.filter(status=TICKET_STATUS_NEW,
#                                 source=TICKET_SOURCE_NEW_SOUND)
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
AND ticket.status = '%s'
""" % TICKET_STATUS_NEW)))

def new_support_tickets_count():
    return Ticket.objects.filter(assignee=None,
                                 source=TICKET_SOURCE_CONTACT_FORM).count()

@permission_required('tickets.can_moderate')
def tickets_home(request):
    
    if request.user.id :
        sounds_in_moderators_queue_count = Ticket.objects.select_related().filter(assignee=request.user.id).exclude(status='closed').exclude(content=None).order_by('status', '-created').count()
    else :
        sounds_in_moderators_queue_count = -1
        
    new_upload_count = new_sound_tickets_count()
    tardy_moderator_sounds_count = len(list(__get_tardy_moderator_tickets_all()))
    tardy_user_sounds_count = len(list(__get_tardy_user_tickets_all()))
    new_support_count = new_support_tickets_count()
    sounds_queued_count = Sound.objects.filter(processing_state='QU').count()
    sounds_pending_count = Sound.objects.filter(processing_state='PE').count()
    sounds_processing_count = Sound.objects.filter(processing_state='PR').count()
    sounds_failed_count = Sound.objects.filter(processing_state='FA').count()
    return render_to_response('tickets/tickets_home.html', locals(), context_instance=RequestContext(request))


def __get_new_uploaders_by_ticket():
#AND (sounds_sound.processing_state = 'OK' OR sounds_sound.processing_state = 'FA')
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
    AND tickets_ticket.status = '%s'
GROUP BY sender_id""" % TICKET_STATUS_NEW)
    user_ids_plus_new_count = dict(cursor.fetchall())
    user_objects = User.objects.filter(id__in=user_ids_plus_new_count.keys())

    users_aux = []
    for user in user_objects:
        # Pick the oldest non moderated ticket of each user and compute how many seconds it has been in the queue
        oldest_new_ticket = Ticket.objects.filter(sender__id=user.id,status=TICKET_STATUS_NEW,content__isnull=False).order_by("created")[0]
        #seconds_in_queue = (datetime.datetime.now() - oldest_new_ticket.created).total_seconds()
        days_in_queue = (datetime.datetime.now() - oldest_new_ticket.created).days #seconds_in_queue / (3600 * 24)
        users_aux.append({'user':user, 'days_in_queue':days_in_queue, 'new_sounds':user_ids_plus_new_count[user.id]})

    # Sort users according to their oldest ticket (older = first)
    users_aux.sort(key=lambda item:item['days_in_queue'], reverse=True)
    new_sounds_users = []
    for user in users_aux:
        new_sounds_users.append((user['user'],user['new_sounds'],user['days_in_queue']))

    return new_sounds_users


def __get_unsure_sound_tickets():
    '''Query to get tickets that were returned to the queue by moderators that
    didn't know what to do with the sound.'''
    return Ticket.objects.filter(source=TICKET_SOURCE_NEW_SOUND,
                                 assignee=None,
                                 status=TICKET_STATUS_ACCEPTED)


def __get_tardy_moderator_tickets():
    """Get tickets for moderators that haven't responded in the last day"""
    return Ticket.objects.raw("""
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
AND ticket.status != '%s'
LIMIT 5
""" % TICKET_STATUS_CLOSED)


def __get_tardy_moderator_tickets_all():
    """Get tickets for moderators that haven't responded in the last day"""
    return Ticket.objects.raw("""
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
AND ticket.status != '%s'
""" % TICKET_STATUS_CLOSED)


def __get_tardy_user_tickets():
    """Get tickets for users that haven't responded in the last 2 days"""
    return Ticket.objects.raw("""
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
LIMIT 5
""" % TICKET_STATUS_CLOSED)
    
def __get_tardy_user_tickets_all():
    """Get tickets for users that haven't responded in the last 2 days"""
    return Ticket.objects.raw("""
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
""" % TICKET_STATUS_CLOSED)


@permission_required('tickets.can_moderate')
def moderation_home(request):
    if request.user.id :
        sounds_in_moderators_queue_count = Ticket.objects.select_related().filter(assignee=request.user.id).exclude(status='closed').exclude(content=None).order_by('status', '-created').count()
    else :
        sounds_in_moderators_queue_count = -1

    new_sounds_users = __get_new_uploaders_by_ticket()
    unsure_tickets = list(__get_unsure_sound_tickets()) #TODO: shouldn't appear
    tardy_moderator_tickets = list(__get_tardy_moderator_tickets())
    tardy_user_tickets = list(__get_tardy_user_tickets())
    tardy_moderator_tickets_count = len(list(__get_tardy_moderator_tickets_all()))
    tardy_user_tickets_count = len(list(__get_tardy_user_tickets_all()))
    
    return render_to_response('tickets/moderation_home.html', locals(), context_instance=RequestContext(request))

@permission_required('tickets.can_moderate')
def moderation_tary_users_sounds(request):
    if request.user.id :
        sounds_in_moderators_queue_count = Ticket.objects.select_related().filter(assignee=request.user.id).exclude(status='closed').exclude(content=None).order_by('status', '-created').count()
    else :
        sounds_in_moderators_queue_count = -1

    tardy_user_tickets = list(__get_tardy_user_tickets_all())

    return render_to_response('tickets/moderation_tardy_users.html', combine_dicts(paginate(request, tardy_user_tickets, 10), locals()), context_instance=RequestContext(request))

@permission_required('tickets.can_moderate')
def moderation_tary_moderators_sounds(request):
    if request.user.id :
        sounds_in_moderators_queue_count = Ticket.objects.select_related().filter(assignee=request.user.id).exclude(status='closed').exclude(content=None).order_by('status', '-created').count()
    else :
        sounds_in_moderators_queue_count = -1

    tardy_moderators_tickets = list(__get_tardy_moderator_tickets_all())

    return render_to_response('tickets/moderation_tardy_moderators.html', combine_dicts(paginate(request, tardy_moderators_tickets, 10), locals()), context_instance=RequestContext(request))


@permission_required('tickets.can_moderate')
def moderation_assign_user(request, user_id):
#AND (sounds_sound.processing_state = 'OK' OR sounds_sound.processing_state = 'FA')
    sender = User.objects.get(id=user_id)
#    Ticket.objects.filter(assignee=None, sender=sender, source=TICKET_SOURCE_NEW_SOUND) \
#        .update(assignee=request.user, status=TICKET_STATUS_ACCEPTED)
    cursor = connection.cursor()
    cursor.execute("""
UPDATE
    tickets_ticket
SET
    assignee_id = %s,
    status = '%s',
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
AND tickets_ticket.status = '%s'
AND sounds_sound.user_id = %s""" % \
(request.user.id, TICKET_STATUS_ACCEPTED, TICKET_STATUS_NEW, sender.id))
    transaction.commit_unless_managed()
    msg = 'You have been assigned all new sounds from %s.' % sender.username
    messages.add_message(request, messages.INFO, msg)
    return HttpResponseRedirect(reverse("tickets-moderation-home"))

# TODO: ongoing work
@permission_required('tickets.can_moderate')
def moderation_assign_single_ticket(request, user_id, ticket_id):
#AND (sounds_sound.processing_state = 'OK' OR sounds_sound.processing_state = 'FA')
    
    # REASSIGN SINGLE TICKET
    ticket = Ticket.objects.get(id=ticket_id)
    sender = User.objects.get(id=user_id)
    ticket.assignee = User.objects.get(id=request.user.id)
    
    '''
    cursor = connection.cursor()
    cursor.execute("""
    UPDATE 
        tickets_ticket 
    SET 
        assignee_id = %s
    WHERE 
        tickets_ticket.id = %s
    """ % \
    (request.user.id, ticket.id))
    transaction.commit_unless_managed()
    '''
    '''
    tc = TicketComment(sender=request.user,
                       text="Reassigned ticket to moderator %s" % request.user.username,
                       ticket=ticket,
                       moderator_only=False)
    tc.save()
    '''
    # update modified date, so it doesn't appear in tardy moderator's sounds
    ticket.modified = datetime.datetime.now()
    ticket.save()
    
    msg = 'You have been assigned ticket "%s".' % ticket.title
    messages.add_message(request, messages.INFO, msg)

    next = request.GET.get("next",None)
    p = request.GET.get("p",1)

    if next:
        if next == "tardy_users":
            return HttpResponseRedirect(reverse("tickets-moderation-tardy-users"))
        elif next == "tardy_moderators":
            return HttpResponseRedirect(reverse("tickets-moderation-tardy-moderators")+"?page=%s"%str(p))
        else:
            return HttpResponseRedirect(reverse("tickets-moderation-home")+"?page=%s"%str(p))
    else:
        return HttpResponseRedirect(reverse("tickets-moderation-home"))


@permission_required('tickets.can_moderate')
def moderation_assigned(request, user_id):
    
    can_view_moderator_only_messages = __can_view_mod_msg(request)
    clear_forms = True
    if request.method == 'POST':
        mod_sound_form = SoundModerationForm(request.POST)
        msg_form = ModerationMessageForm(request.POST)

        if mod_sound_form.is_valid() and msg_form.is_valid():

            ticket = Ticket.objects.get(id=mod_sound_form.cleaned_data.get("ticket", False))
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
                ticket.content.content_object.moderation_state = "OK"
                ticket.content.content_object.save()
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
                # Get all currently pending sound tickets for user
                whitelist_user = ticket.sender
                whitelist_user.profile.is_whitelisted = True
                whitelist_user.profile.save()
                pending_tickets = Ticket.objects.filter(sender=whitelist_user,
                                                        source='new sound') \
                                                .exclude(status=TICKET_STATUS_CLOSED)
                # Set all sounds to OK and the tickets to closed
                for pending_ticket in pending_tickets:
                    if pending_ticket.content:
                        pending_ticket.content.content_object.moderation_state = "OK"
                        pending_ticket.content.content_object.save()
                        pending_ticket.content.content_object.mark_index_dirty()
                    # This could be done with a single update, but there's a chance
                    # we lose a sound that way (a newly created ticket who's sound
                    # is not set to OK, but the ticket is closed).
                    pending_ticket.status = TICKET_STATUS_CLOSED
                    pending_ticket.save()
                ticket.send_notification_emails(Ticket.NOTIFICATION_WHITELISTED,
                                                Ticket.USER_ONLY)
        else:
            clear_forms = False
    if clear_forms:
        mod_sound_form = SoundModerationForm(initial={'action':'Approve'})
        msg_form = ModerationMessageForm()
    moderator_tickets = Ticket.objects.select_related() \
                            .filter(assignee=user_id) \
                            .exclude(status=TICKET_STATUS_CLOSED) \
                            .exclude(content=None) \
                            .order_by('status', '-created')
    moderator_tickets_count = len(moderator_tickets)
    moderation_texts = MODERATION_TEXTS
    return render_to_response('tickets/moderation_assigned.html',
                              locals(),
                              context_instance=RequestContext(request))


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
    return render_to_response('tickets/user_annotations.html',
                              locals(),
                              context_instance=RequestContext(request))


@permission_required('tickets.can_moderate')
def support_home(request):
    return HttpResponse('TODO')
