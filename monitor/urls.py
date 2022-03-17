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
import monitor.views

urlpatterns = [

    url(r'^$', monitor.views.monitor_home, name='monitor-home'),

    url(r'^processing/process_sounds/$', monitor.views.process_sounds, name='monitor-processing-process'),
    url(r'^stats/$', monitor.views.monitor_stats, name='monitor-stats'),
    url(r'^queues_stats/$', monitor.views.get_queues_status, name='queues-stats'),
    url(r'^moderators_stats/$', monitor.views.moderators_stats, name='monitor-moderators-stats'),
    url(r'^totals_stats_ajax/$', monitor.views.totals_stats_ajax, name='monitor-totals-stats-ajax'),
    url(r'^ajax_tags_stats/$', monitor.views.tags_stats_ajax, name='monitor-tags-stats-ajax'),
    url(r'^ajax_queries_stats/$', monitor.views.queries_stats_ajax, name='monitor-queries-stats-ajax'),
    url(r'^ajax_downloads_stats/$', monitor.views.downloads_stats_ajax, name='monitor-downloads-stats-ajax'),
    url(r'^ajax_donations_stats/$', monitor.views.donations_stats_ajax, name='monitor-donations-stats-ajax'),
    url(r'^ajax_sounds_stats/$', monitor.views.sounds_stats_ajax, name='monitor-sounds-stats-ajax'),
    url(r'^ajax_users_stats/$', monitor.views.users_stats_ajax, name='monitor-users-stats-ajax'),
    url(r'^ajax_active_users_stats/$', monitor.views.active_users_stats_ajax, name='monitor-active-users-stats-ajax'),
    url(r'^ajax_moderator_stats/$', monitor.views.moderator_stats_ajax, name='monitor-moderator-stats-ajax'),

]
