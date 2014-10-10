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

from rest_framework.exceptions import APIException
from rest_framework import status
import logging

logger = logging.getLogger("api_errors")


## TODO: This function is defined in apiv2_utils, but it can not be imported here because of circular imports
def basic_request_info_for_log_message(auth_method_name, developer, user, client_id, ip):
    return 'ApiV2 Auth:%s Dev:%s User:%s Client:%s Ip:%s' % (auth_method_name, developer, user, str(client_id), ip)


class NotFoundException(APIException):
    detail = None
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, msg="Not found", resource=None):
        request_info = '-'
        if resource:
            request_info = basic_request_info_for_log_message(resource.auth_method_name, resource.developer, resource.user, resource.client_id, resource.end_user_ip)
        logger.error('<%i Not found> %s (%s)' % (self.status_code, msg, request_info))
        self.detail = msg


class InvalidUrlException(APIException):
    detail = None
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, msg="Invalid url", request_info='-'):
        logger.error('<%i Invalid url> %s (%s)' % (self.status_code, msg, request_info))
        self.detail = msg


class BadRequestException(APIException):
    detail = None
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, msg="Bad request", resource=None):
        request_info = '-'
        if resource:
            request_info = basic_request_info_for_log_message(resource.auth_method_name, resource.developer, resource.user, resource.client_id, resource.end_user_ip)
        logger.error('<%i Bad request> %s (%s)' % (self.status_code, msg, request_info))
        self.detail = msg


class ConflictException(APIException):
    detail = None
    status_code = status.HTTP_409_CONFLICT

    def __init__(self, msg="Conflict", resource=None):
        request_info = '-'
        if resource:
            request_info = basic_request_info_for_log_message(resource.auth_method_name, resource.developer, resource.user, resource.client_id, resource.end_user_ip)
        logger.error('<%i Conflict> %s (%s)' % (self.status_code, msg, request_info))
        self.detail = msg


class UnauthorizedException(APIException):
    detail = None
    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self, msg="Not authorized", resource=None):
        request_info = '-'
        if resource:
            request_info = basic_request_info_for_log_message(resource.auth_method_name, resource.developer, resource.user, resource.client_id, resource.end_user_ip)
        logger.error('<%i Not authorized> %s (%s)' % (self.status_code, msg, request_info))
        self.detail = msg


class RequiresHttpsException(APIException):
    detail = None
    status_code = status.HTTP_403_FORBIDDEN

    def __init__(self, msg="This resource requires a secure connection (https)", request_info='-'):
        logger.error('<%i Requires Https> %s (%s)' % (self.status_code, msg, request_info))
        self.detail = msg


class ServerErrorException(APIException):
    detail = None
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, msg="Server error", resource=None):
        request_info = '-'
        if resource:
            request_info = basic_request_info_for_log_message(resource.auth_method_name, resource.developer, resource.user, resource.client_id, resource.end_user_ip)
        logger.error('<%i Server error> %s (%s)' % (self.status_code, msg, request_info))
        self.detail = msg


class OtherException(APIException):
    detail = None
    status_code = None

    def __init__(self, msg="Bad request", status=status.HTTP_400_BAD_REQUEST, resource=None):
        request_info = '-'
        if resource:
            request_info = basic_request_info_for_log_message(resource.auth_method_name, resource.developer, resource.user, resource.client_id, resource.end_user_ip)
        logger.error('<%i Other exception> %s (%s)' % (status, msg, request_info))
        self.detail = msg
        self.status_code = status


class Throttled(APIException):
    detail = None
    status_code = status.HTTP_429_TOO_MANY_REQUESTS

    def __init__(self, msg="Request was throttled", request_info='-'):
        logger.error('<%i Throttled> %s (%s)' % (self.status_code, msg, request_info))
        self.detail = msg