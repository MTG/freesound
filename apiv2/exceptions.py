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


from rest_framework import status
from rest_framework.exceptions import APIException


class LoggedAPIException(APIException):
    # An APIException, which when handled by our exception handler will also emit a log message
    # to the specified logger.
    summary_label = None
    report_to_sentry = False

    def __init__(self, msg=None, *, resource=None, request=None):
        self.detail = msg if msg is not None else self.default_detail
        self.log_resource = resource
        self.log_request = request


class NotFoundException(LoggedAPIException):
    status_code = status.HTTP_404_NOT_FOUND
    summary_label = "Not found"
    default_detail = "Not found"


class InvalidUrlException(LoggedAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    summary_label = "Invalid url"
    default_detail = "Invalid url"


class BadRequestException(LoggedAPIException):
    status_code = status.HTTP_400_BAD_REQUEST
    summary_label = "Bad request"
    default_detail = "Bad request"


class ConflictException(LoggedAPIException):
    status_code = status.HTTP_409_CONFLICT
    summary_label = "Conflict"
    default_detail = "Conflict"


class UnauthorizedException(LoggedAPIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    summary_label = "Not authorized"
    default_detail = "Not authorized"


class RequiresHttpsException(LoggedAPIException):
    status_code = status.HTTP_403_FORBIDDEN
    summary_label = "Requires Https"
    default_detail = "This resource requires a secure connection (https)"


class ServerErrorException(LoggedAPIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    summary_label = "Server error"
    default_detail = "Server error"
    report_to_sentry = True


class Throttled(LoggedAPIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    summary_label = "Throttled"
    default_detail = "Request was throttled"
