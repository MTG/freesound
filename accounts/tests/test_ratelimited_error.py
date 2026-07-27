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

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from accounts.views import ratelimited_error
from utils.ratelimit import request_limit_events_total
from utils.test_helpers import counter_samples


def _samples():
    return counter_samples(request_limit_events_total, "reason", "enforced", "user_type")


def test_ratelimited_error_returns_429_and_counts_event():
    # ratelimited_error helper increments a prometheus counter
    request = RequestFactory().get("/search/")
    request.user = AnonymousUser()
    before = _samples().get(("django_ratelimit", "true", "anonymous"), 0)

    response = ratelimited_error(request, Exception())

    assert response.status_code == 429
    assert _samples()[("django_ratelimit", "true", "anonymous")] == before + 1
