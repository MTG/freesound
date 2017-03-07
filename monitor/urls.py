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

from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from django.conf.urls import patterns, url
import monitor.views

urlpatterns = [

    url(r'^$', monitor.views.monitor_home, name='monitor-home'),

    url(r'^processing/process_sounds/$', monitor.views.process_sounds,
        name='monitor-processing-process'),
    url(r'^stats/$',
        login_required(TemplateView.as_view(template_name='monitor/stats.html')),
        name='monitor-stats'),
    url(r'^total_users_stats_ajax/$', monitor.views.total_users_stats_ajax,
        name='monitor-total-users-stats-ajax'),
    url(r'^total_sounds_stats_ajax/$', monitor.views.total_sounds_stats_ajax,
        name='monitor-total-sounds-stats-ajax'),
    url(r'^total_activity_stats_ajax/$', monitor.views.total_activity_stats_ajax,
        name='monitor-total-activity-stats-ajax'),
    url(r'^total_tags_stats_ajax/$', monitor.views.total_tags_stats_ajax,
        name='monitor-total-tags-stats-ajax'),
    url(r'^total_forum_stats_ajax/$', monitor.views.total_forum_stats_ajax,
        name='monitor-total-forum-stats-ajax'),
    url(r'^ajax_tags_stats/$', monitor.views.tags_stats_ajax,
        name='monitor-tags-stats-ajax'),
    url(r'^ajax_downloads_stats/$', monitor.views.downloads_stats_ajax,
        name='monitor-downloads-stats-ajax'),
    url(r'^ajax_donations_stats/$', monitor.views.donations_stats_ajax,
        name='monitor-donations-stats-ajax'),
    url(r'^ajax_sounds_stats/$', monitor.views.sounds_stats_ajax,
        name='monitor-sounds-stats-ajax'),
    url(r'^ajax_users_stats/$', monitor.views.users_stats_ajax,
        name='monitor-users-stats-ajax'),

]
