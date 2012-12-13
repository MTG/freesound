# -*- coding: utf-8 -*-

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

    url(r'^guide/$',
        direct_to_template,
        {'template': 'tickets/guide.html'},
        name='tickets-moderation-guide'),

    url(r'^moderation/$',
        moderation_home,
        name='tickets-moderation-home'),

    url(r'^moderation/tardy_users_sounds/$',
        moderation_tary_users_sounds,
        name='tickets-moderation-tardy-users'),

    url(r'^moderation/tardy_moderators_sounds/$',
        moderation_tary_moderators_sounds,
        name='tickets-moderation-tardy-moderators'),

    url(r'^moderation/assign/(?P<user_id>\d+)/$',
        moderation_assign_user,
        name='tickets-moderation-assign-user'),

    url(r'^moderation/assign/ticket/(?P<user_id>\d+)/(?P<ticket_id>\d+)/$',
        moderation_assign_single_ticket,
        name='tickets-moderation-assign-signle-ticket'),

    url(r'^moderation/assigned/(?P<user_id>\d+)/$',
        moderation_assigned,
        name='tickets-moderation-assigned'),

    url(r'^support/$',
        support_home,
        name='tickets-support-home'),

    url(r'^moderation/annotations/(?P<user_id>\d+)/$',
        user_annotations,
        name='tickets-user-annotations'),

    url(r'^(?P<ticket_key>[\w\d]+)/$',
        ticket,
        name='tickets-ticket'),

    url(r'^(?P<ticket_key>[\w\d]+)/messages/$',
        sound_ticket_messages,
        name='tickets-ticket-messages'),

)
