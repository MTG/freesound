# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns, url
from views import ticket, tickets, new_contact_ticket, \
    moderation_home, moderation_sounds, moderation_support, \
    moderation_sounds_assign_user, test_moderation_panel

urlpatterns = patterns('',

    #url(r'^new/$', 
    #    new_ticket, 
    #    name="tickets-new"),
    
    url(r'^contact/$', 
        new_contact_ticket, 
        name='tickets-contact'),
        
    url(r'^moderation/$',
        moderation_home,
        name='tickets-moderation'),
        
    url(r'^moderation/sounds/$',
        moderation_sounds,
        name='tickets-moderation-sounds'),
        
    url(r'^moderation/sounds/assign/(?P<user_id>\d+)/$',
        moderation_sounds_assign_user,
        name='tickets-moderation-sounds-asign-user'),
        
    url(r'^moderation/support/$',
        moderation_support,
        name='tickets-moderation-support'),
            
    url(r'^moderation/testpanel/$',
        test_moderation_panel),
        
    url(r'^(?P<ticket_key>[\w\d]+)/$', 
        ticket, 
        name='tickets-ticket'),
        
    url(r'^$',
        tickets, 
        name='tickets-tickets'),
)