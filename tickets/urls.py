# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns, url
from django.views.generic.simple import direct_to_template
from views import *

urlpatterns = patterns('',

    #url(r'^new/$', 
    #    new_ticket, 
    #    name="tickets-new"),
    
    url(r'^contact/$', 
        new_contact_ticket, 
        name='tickets-contact'),
        
    url(r'^$',
        tickets_home,
        name='tickets-home'),
        
    url(r'^moderation/$',
        moderation_home,
        name='tickets-moderation-home'),
        
    url(r'^moderation/assign/(?P<user_id>\d+)/$',
        moderation_assign_user,
        name='tickets-moderation-asign-user'),
        
    url(r'^moderation/assigned/(?P<user_id>\d+)/$',
        moderation_assigned,
        name='tickets-moderation-asigned'),
        
    url(r'^moderation/sounds/(?P<sound_id>\d+)/display$', 
        direct_to_template, 
        {'template':'tickets/moderation_sound_display.html'}, 
        name="tickets-sound-display"),
        
    url(r'^support/$',
        support_home,
        name='tickets-support-home'),
            
    url(r'^moderation/testpanel/$',
        test_moderation_panel),
        
    url(r'^(?P<ticket_key>[\w\d]+)/$', 
        ticket, 
        name='tickets-ticket'),
        
    url(r'^$',
        tickets, 
        name='tickets-tickets'),
)