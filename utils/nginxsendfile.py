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

from django.http import HttpResponse,Http404
from django.conf import settings
from wsgiref.util import FileWrapper

import os

def sendfile(path, attachment_name, secret_url = None):
    if not os.path.exists(path):
        raise Http404
    
    if settings.DEBUG:
        response = HttpResponse(FileWrapper(file(path, "rb")))
        response['Content-Length'] = os.path.getsize(path)
    else:
        response = HttpResponse()
        response['X-Accel-Redirect'] = secret_url

    response['Content-Type']="application/octet-stream"
    response['Content-Disposition'] = "attachment; filename=\"%s\"" % attachment_name
    
    return response
