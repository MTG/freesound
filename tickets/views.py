from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from models import Ticket, Queue, TicketComment
from forms import *
from tickets import *
from django.db import connection, transaction
from django.contrib import messages
from sounds.models import Sound

def __get_contact_form(request, use_post=True):
    return __get_anon_or_user_form(request, AnonymousContactForm, UserContactForm, use_post)
    
def __get_tc_form(request, use_post=True):
    return __get_anon_or_user_form(request, AnonymousMessageForm, UserMessageForm, use_post)

def __get_anon_or_user_form(request, anonymous_form, user_form, use_post=True):
    if len(request.POST.keys()) > 0 and use_post:
        if request.user.is_authenticated():
            return user_form(request.POST)
        else:
            return anonymous_form(request, request.POST)
    else:
        return user_form() if request.user.is_authenticated() else anonymous_form(request)
        

def ticket(request, ticket_key):
    ticket = get_object_or_404(Ticket, key=ticket_key)
    if request.method == 'POST':
        form = __get_tc_form(request)
        if form.is_valid():
            tc = TicketComment()
            tc.text = form.cleaned_data['message']
            if request.user.is_authenticated():
                tc.sender = request.user
            tc.ticket = ticket
            tc.save()
    else:
        form = __get_tc_form(request, False)
    return render_to_response('tickets/ticket.html', 
                              locals(), context_instance=RequestContext(request))
    
@login_required
def tickets(request):
    tickets = Ticket.objects.all()
    return render_to_response('tickets/tickets.html', 
                              locals(), context_instance=RequestContext(request))


def new_contact_ticket(request):
    ticket_created = False
    if request.POST:    
        form = __get_contact_form(request)
        if form.is_valid():
            ticket = Ticket()
            ticket.title = form.cleaned_data['title']
            ticket.source = TICKET_SOURCE_CONTACT_FORM
            ticket.status = TICKET_STATUS_NEW
            ticket.queue  = Queue.objects.get(name=QUEUE_SUPPORT_REQUESTS)
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

#TODO: check for right permissions (all moderation functions)
@login_required
def tickets_home(request):
    new_upload_count = Ticket.objects.filter(assignee=None,
                                             source=TICKET_SOURCE_NEW_SOUND).count()
    new_support_count = Ticket.objects.filter(assignee=None,
                                              source=TICKET_SOURCE_CONTACT_FORM).count()
    return render_to_response('tickets/tickets_home.html', locals(), context_instance=RequestContext(request))


def __get_new_uploaders_by_ticket():
    cursor = connection.cursor()
    cursor.execute("""
SELECT sender_id, count(*) from tickets_ticket 
WHERE source = 'new sound' 
AND assignee_id is Null 
AND status = '%s'
GROUP BY sender_id""" % TICKET_STATUS_NEW)
    user_ids_plus_new_count = dict(cursor.fetchall())
    user_objects = User.objects.filter(id__in=user_ids_plus_new_count.keys())
    users_plus_new_count = {}
    for user in user_objects:
        users_plus_new_count[user] = user_ids_plus_new_count[user.id]
    # looks nicer, but probably less efficient
    #return [(User.objects.get(id=id).username, count) \
    #        for id,count in user_ids_plus_new_count.items()]
    return users_plus_new_count

def __get_unsure_sound_tickets():
    return Ticket.objects.filter(source=TICKET_SOURCE_NEW_SOUND, 
                                 assignee=None, 
                                 status=TICKET_STATUS_ACCEPTED)

def __get_tardy_moderator_tickets():
    """Get tickets for moderators that haven't responded in the last 2 days"""
    return Ticket.objects.raw("""
SELECT
ticket.id
FROM 
tickets_ticketcomment AS comment,
tickets_ticket AS ticket
WHERE comment.id in (   SELECT MAX(id)
                        FROM tickets_ticketcomment
                        GROUP BY ticket_id    )
AND ticket.assignee_id is Not Null
AND comment.ticket_id = ticket.id
AND comment.sender_id = ticket.sender_id
AND now() - comment.created > INTERVAL '2 days'
    """)
    
def __get_tardy_user_tickets():
    """Get tickets for users that haven't responded in the last 2 days"""
    return Ticket.objects.raw("""
SELECT
ticket.id
FROM 
tickets_ticketcomment AS comment,
tickets_ticket AS ticket
WHERE comment.id in (   SELECT MAX(id)
                        FROM tickets_ticketcomment
                        GROUP BY ticket_id    )
AND ticket.assignee_id is Not Null
AND comment.ticket_id = ticket.id
AND comment.sender_id != ticket.sender_id
AND now() - comment.created > INTERVAL '2 days'
""")

@login_required
def moderation_home(request):
    new_sounds_users = __get_new_uploaders_by_ticket()
    unsure_tickets = __get_unsure_sound_tickets()
    tardy_moderator_tickets = __get_tardy_moderator_tickets()
    tardy_user_tickets = __get_tardy_user_tickets()
    return render_to_response('tickets/moderation_home.html', locals(), context_instance=RequestContext(request))

@login_required
def moderation_assign_user(request, user_id):
    sender = User.objects.get(id=user_id)
    Ticket.objects.filter(assignee=None, sender=sender, source=TICKET_SOURCE_NEW_SOUND) \
        .update(assignee=request.user, status=TICKET_STATUS_ACCEPTED)
    msg = 'You have been assigned all new sounds from %s.' % sender.username
    messages.add_message(request, messages.INFO, msg)
    return HttpResponseRedirect(reverse("tickets-moderation-home"))
    
@login_required
def moderation_assigned(request, user_id):
    clear_forms = True
    if request.method == 'POST':
        mod_sound_form = SoundModerationForm(request.POST)
        msg_form = ModerationMessageForm(request.POST) 
        
        if mod_sound_form.is_valid() and msg_form.is_valid():
            
            ticket = Ticket.objects.get(id=mod_sound_form.cleaned_data.get("ticket",False))
            action = mod_sound_form.cleaned_data.get("action")
            msg = msg_form.cleaned_data.get("message", False)
            
            if msg:
                tc = TicketComment(sender=ticket.assignee, 
                                   text=msg, 
                                   ticket=ticket, 
                                   moderator_only=(True if action == 'Defer' else False))
                tc.save()
                    
            if action=="Approve":
                ticket.status=TICKET_STATUS_CLOSED
                ticket.content.content_object.moderation_state="OK"
                ticket.content.content_object.save()
            elif action=="Defer":
                ticket.status=TICKET_STATUS_DEFERRED
            elif action=="Return":
                ticket.assignee=None
                ticket.status=TICKET_STATUS_ACCEPTED
            elif action=="Delete":
                ticket.content.content_object.delete()
                ticket.content.delete()
                ticket.content = None
                ticket.status=TICKET_STATUS_CLOSED
            ticket.save()
        else:
            clear_forms = False
    if clear_forms:
        mod_sound_form = SoundModerationForm()
        msg_form = ModerationMessageForm()
    moderator_tickets = Ticket.objects.select_related() \
                            .filter(assignee=user_id) \
                            .exclude(status=TICKET_STATUS_CLOSED)
    moderation_texts = MODERATION_TEXTS
    return render_to_response('tickets/moderation_assigned.html',
                              locals(),
                              context_instance=RequestContext(request))


@login_required
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

@login_required
def support_home(request):
    return HttpResponse('TODO')
