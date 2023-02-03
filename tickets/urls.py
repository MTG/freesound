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

from django.conf.urls import url
from tickets import views

urlpatterns = [

    url(r'^moderation/$',
        views.moderation_home,
        name='tickets-moderation-home'),

    url(r'^moderation/tardy_users_sounds/$',
        views.moderation_tardy_users_sounds,
        name='tickets-moderation-tardy-users'),

    url(r'^moderation/tardy_moderators_sounds/$',
        views.moderation_tardy_moderators_sounds,
        name='tickets-moderation-tardy-moderators'),

    url(r'^moderation/assign/new/$',
        views.moderation_assign_all_new,
        name='tickets-moderation-assign-all-new'),

    url(r'^moderation/assign/(?P<user_id>\d+)/new$',
        views.moderation_assign_user,
        name='tickets-moderation-assign-user-new'),

    url(r'^moderation/assign/(?P<user_id>\d+)/pending$',
        views.moderation_assign_user_pending,
        name='tickets-moderation-assign-user-pending'),

    url(r'^moderation/assigned/(?P<user_id>\d+)/$',
        views.moderation_assigned,
        name='tickets-moderation-assigned'),

    url(r'^moderation/assign/ticket/(?P<user_id>\d+)/(?P<ticket_id>\d+)/$',
        views.moderation_assign_single_ticket,
        name='tickets-moderation-assign-single-ticket'),

    url(r'^moderation/annotations/(?P<user_id>\d+)/$',
        views.user_annotations,
        name='tickets-user-annotations'),

    url(r'^moderation/pending/(?P<username>[^//]+)/$',
        views.pending_tickets_per_user,
        name='tickets-user-pending_sounds'),

    url(r'^(?P<ticket_key>[\w\d]+)/$',
        views.ticket,
        name='tickets-ticket'),

    url(r'^(?P<ticket_key>[\w\d]+)/messages/$',
        views.sound_ticket_messages,
        name='tickets-ticket-messages'),
]
