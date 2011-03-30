# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns, url
from views import ticket, tickets, new_contact_ticket

urlpatterns = patterns('',
    

    #url(r'^new/$', 
    #    new_ticket, 
    #    name="tickets-new"),
    
    url(r'^contact/$', 
        new_contact_ticket, 
        name="tickets-contact"),
        
    url(r'^(?P<ticket_key>[\w\d]+)/$', 
        ticket, 
        name="tickets-ticket"),
        
    url(r'^$',
        tickets, 
        name="tickets-tickets"),
)