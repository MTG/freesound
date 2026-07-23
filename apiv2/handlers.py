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


import logging

import sentry_sdk
from rest_framework.views import exception_handler as drf_exception_handler

from apiv2.apiv2_utils import log_message_helper
from apiv2.exceptions import LoggedAPIException, Throttled
from utils.ratelimit import RequestLimitReason, count_request_limit_event

errors_logger = logging.getLogger("api_errors")


def api_exception_handler(exc, context):
    # If the exception is one of our specific API handlers, send a
    # message to the log handler, sentry, and prometheus, if configured
    response = drf_exception_handler(exc, context)
    if isinstance(exc, LoggedAPIException):
        summary = f"{exc.status_code} {exc.summary_label}"
        errors_logger.info(
            log_message_helper(
                summary,
                data_dict={
                    "summary_message": summary,
                    "long_message": exc.detail,
                    "status": exc.status_code,
                },
                resource=exc.log_resource,
                request=exc.log_request,
            )
        )
        if exc.report_to_sentry:
            sentry_sdk.capture_exception(exc)
        if isinstance(exc, Throttled) and exc.log_request is not None:
            count_request_limit_event(exc.log_request, RequestLimitReason.API_THROTTLE, enforced=True)
    return response
