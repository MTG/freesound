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


class NotFoundException(APIException):
    detail = None
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, msg="Not found"):
        self.detail = msg


class InvalidUrlException(APIException):
    detail = None
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, msg="Bad request"):
        self.detail = msg


class UnauthorizedException(APIException):
    detail = None
    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self, msg="Not authorized"):
        self.detail = msg


class RequiresHttpsException(APIException):
    detail = None
    status_code = status.HTTP_403_FORBIDDEN

    def __init__(self, msg="This resource requires a secure connection (https)"):
        self.detail = msg


class ServerErrorException(APIException):
    detail = None
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, msg="Server error"):
        self.detail = msg


class OtherException(APIException):
    detail = None
    status_code = None

    def __init__(self, msg="Bad request", status=status.HTTP_400_BAD_REQUEST):
        self.detail = msg
        self.status = status