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
import monitor.views

urlpatterns = [

    path('', monitor.views.monitor_home, name='monitor-home'),

    path('processing/process_sounds/', monitor.views.process_sounds, name='monitor-processing-process'),
    path('stats/', monitor.views.monitor_stats, name='monitor-stats'),
    path('queues_stats/', monitor.views.get_queues_status, name='queues-stats'),
    path('moderators_stats/', monitor.views.moderators_stats, name='monitor-moderators-stats'),
    path('totals_stats_ajax/', monitor.views.totals_stats_ajax, name='monitor-totals-stats-ajax'),
    path('ajax_tags_stats/', monitor.views.tags_stats_ajax, name='monitor-tags-stats-ajax'),
    path('ajax_queries_stats/', monitor.views.queries_stats_ajax, name='monitor-queries-stats-ajax'),
    path('ajax_downloads_stats/', monitor.views.downloads_stats_ajax, name='monitor-downloads-stats-ajax'),
    path('ajax_donations_stats/', monitor.views.donations_stats_ajax, name='monitor-donations-stats-ajax'),
    path('ajax_sounds_stats/', monitor.views.sounds_stats_ajax, name='monitor-sounds-stats-ajax'),
    path('ajax_users_stats/', monitor.views.users_stats_ajax, name='monitor-users-stats-ajax'),
    path('ajax_active_users_stats/', monitor.views.active_users_stats_ajax, name='monitor-active-users-stats-ajax'),
    path('ajax_moderator_stats/', monitor.views.moderator_stats_ajax, name='monitor-moderator-stats-ajax'),

]
