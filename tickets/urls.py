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

from django.urls import path
from tickets import views

urlpatterns = [
    path('moderation/', views.assign_sounds, name='tickets-moderation-home'),
    path('moderation/guide', views.guide, name='tickets-moderation-guide'),
    path('moderation/tardy_users_sounds/', views.moderation_tardy_users_sounds, name='tickets-moderation-tardy-users'),
    path(
        'moderation/tardy_moderators_sounds/',
        views.moderation_tardy_moderators_sounds,
        name='tickets-moderation-tardy-moderators'
    ),
    path('moderation/assign/new/', views.moderation_assign_all_new, name='tickets-moderation-assign-all-new'),
    path(
        'moderation/assign/<int:user_id>/new', views.moderation_assign_user, name='tickets-moderation-assign-user-new'
    ),
    path(
        'moderation/assign/<int:user_id>/pending',
        views.moderation_assign_user_pending,
        name='tickets-moderation-assign-user-pending'
    ),
    path('moderation/assigned/<int:user_id>/', views.moderation_assigned, name='tickets-moderation-assigned'),
    path(
        'moderation/assign/ticket/<int:ticket_id>/',
        views.moderation_assign_single_ticket,
        name='tickets-moderation-assign-single-ticket'
    ),
    path('moderation/annotations/<int:user_id>/', views.user_annotations, name='tickets-user-annotations'),
    path('moderation/annotations/add/<int:user_id>/', views.add_user_annotation, name='tickets-add-user-annotation'),
    path('moderation/pending/<username>/', views.pending_tickets_per_user, name='tickets-user-pending_sounds'),
    path('<ticket_key>/', views.ticket, name='tickets-ticket'),
    path('moderation/whitelist/<int:user_id>/', views.whitelist_user, name='tickets-whitelist-user'),
]
