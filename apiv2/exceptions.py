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

from rest_framework import status
from rest_framework.exceptions import APIException

import apiv2.apiv2_utils    # absolute import because of mutual imports of this module and apiv2_utils

errors_logger = logging.getLogger("api_errors")


class NotFoundException(APIException):
    detail = None
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, msg="Not found", resource=None):
        summary_message = '%i Not found' % self.status_code
        errors_logger.info(
            apiv2.apiv2_utils.log_message_helper(
                summary_message,
                data_dict={
                    'summary_message': summary_message,
                    'long_message': msg,
                    'status': self.status_code
                },
                resource=resource
            )
        )
        self.detail = msg


class InvalidUrlException(APIException):
    detail = None
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, msg="Invalid url", request=None):
        summary_message = '%i Invalid url' % self.status_code
        errors_logger.info(
            apiv2.apiv2_utils.log_message_helper(
                summary_message,
                data_dict={
                    'summary_message': summary_message,
                    'long_message': msg,
                    'status': self.status_code
                },
                request=request
            )
        )
        self.detail = msg


class BadRequestException(APIException):
    detail = None
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, msg="Bad request", resource=None):
        summary_message = '%i Bad request' % self.status_code
        errors_logger.info(
            apiv2.apiv2_utils.log_message_helper(
                summary_message,
                data_dict={
                    'summary_message': summary_message,
                    'long_message': msg,
                    'status': self.status_code
                },
                resource=resource
            )
        )
        self.detail = msg


class ConflictException(APIException):
    detail = None
    status_code = status.HTTP_409_CONFLICT

    def __init__(self, msg="Conflict", resource=None):
        summary_message = '%i Conflict' % self.status_code
        errors_logger.info(
            apiv2.apiv2_utils.log_message_helper(
                summary_message,
                data_dict={
                    'summary_message': summary_message,
                    'long_message': msg,
                    'status': self.status_code
                },
                resource=resource
            )
        )
        self.detail = msg


class UnauthorizedException(APIException):
    detail = None
    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self, msg="Not authorized", resource=None):
        summary_message = '%i Not authorized' % self.status_code
        errors_logger.info(
            apiv2.apiv2_utils.log_message_helper(
                summary_message,
                data_dict={
                    'summary_message': summary_message,
                    'long_message': msg,
                    'status': self.status_code
                },
                resource=resource
            )
        )
        self.detail = msg


class RequiresHttpsException(APIException):
    detail = None
    status_code = status.HTTP_403_FORBIDDEN

    def __init__(self, msg="This resource requires a secure connection (https)", request=None):
        summary_message = '%i Requires Https' % self.status_code
        errors_logger.info(
            apiv2.apiv2_utils.log_message_helper(
                summary_message,
                data_dict={
                    'summary_message': summary_message,
                    'long_message': msg,
                    'status': self.status_code
                },
                request=request
            )
        )
        self.detail = msg


class ServerErrorException(APIException):
    detail = None
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, msg="Server error", resource=None):
        summary_message = '%i Server error' % self.status_code
        errors_logger.info(
            apiv2.apiv2_utils.log_message_helper(
                summary_message,
                data_dict={
                    'summary_message': summary_message,
                    'long_message': msg,
                    'status': self.status_code
                },
                resource=resource
            )
        )
        self.detail = msg
        sentry_sdk.capture_exception(
            self
        )    # Manually capture exception so it has mroe info and Sentry can organize it properly


class OtherException(APIException):
    detail = None
    status_code = None

    def __init__(self, msg="Bad request", status=status.HTTP_400_BAD_REQUEST, resource=None):
        summary_message = '%i Other exception' % status
        errors_logger.info(
            apiv2.apiv2_utils.log_message_helper(
                summary_message,
                data_dict={
                    'summary_message': summary_message,
                    'long_message': msg,
                    'status': status
                },
                resource=resource
            )
        )
        self.detail = msg
        self.status_code = status


class Throttled(APIException):
    detail = None
    status_code = status.HTTP_429_TOO_MANY_REQUESTS

    def __init__(self, msg="Request was throttled", request=None):
        summary_message = '%i Throttled' % self.status_code
        errors_logger.info(
            apiv2.apiv2_utils.log_message_helper(
                summary_message,
                data_dict={
                    'summary_message': summary_message,
                    'long_message': msg,
                    'status': self.status_code
                },
                request=request
            )
        )
        self.detail = msg
