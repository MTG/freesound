from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
#from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest, Http404

from models import Ticket, Queue, Message
from forms import *
from tickets import *


def __get_contact_form(request, use_post=True):
    return __get_anon_or_user_form(request, AnonymousContactForm, UserContactForm, use_post)
    
def __get_message_form(request, use_post=True):
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
        form = __get_message_form(request)
        if form.is_valid():
            message = Message()
            message.text = form.cleaned_data['message']
            if request.user.is_authenticated():
                message.sender = request.user
            message.ticket = ticket
            message.save()
    else:
        form = __get_message_form(request, False)
    return render_to_response('tickets/ticket.html', 
                              locals(), context_instance=RequestContext(request))
    
@login_required
def tickets(request):
    tickets = Ticket.objects.all()
    return render_to_response('tickets/tickets.html', 
                              locals(), context_instance=RequestContext(request))
    
'''
@login_required
def new_ticket(request):
    print 'blaat'
    if request.method == 'POST':
        print 'POST'
        form = TicketForm(request.POST)
        if form.is_valid():
            # TODO: save ticket
            return redirect(reverse('tickets-ticket', args=[2]))
    else:
        print 'blaat2'
        form = TicketForm()
        print form
        
    return render_to_response('tickets/new_ticket.html', 
                              locals(), context_instance=RequestContext(request))
'''

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
            message = Message()
            if request.user.is_authenticated():
                ticket.sender = request.user
                message.sender = request.user
            else:
                ticket.sender_email = form.cleaned_data['email']
            message.text = form.cleaned_data['message']
            ticket.save()
            message.ticket = ticket
            message.save()
            ticket_created = True
            # TODO: send email
    else:
        form = __get_contact_form(request, False)
    return render_to_response('tickets/contact.html', locals(), context_instance=RequestContext(request))
