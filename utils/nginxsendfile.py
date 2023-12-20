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

import os

from django.http import HttpResponse, Http404
from django.conf import settings
from wsgiref.util import FileWrapper


def prepare_sendfile_arguments_for_sound_download(sound):
    sound_path = sound.locations("path")
    sound_friendly_filename = sound.friendly_filename()
    sound_sendfile_url = sound.locations("sendfile_url")

    if settings.USE_PREVIEWS_WHEN_ORIGINAL_FILES_MISSING and not os.path.exists(sound_path):
        sound_path = sound.locations("preview.LQ.mp3.path")
        sound_friendly_filename = f"{sound_friendly_filename[:sound_friendly_filename.rfind('.')]}.mp3"
        sound_sendfile_url = f"{sound_sendfile_url[:sound_sendfile_url.rfind('.')]}.mp3"

    return sound_path, sound_friendly_filename, sound_sendfile_url


def sendfile(path, attachment_name, secret_url=None):
    if not os.path.exists(path):
        raise Http404

    if settings.DEBUG:
        response = HttpResponse(FileWrapper(open(path, "rb")))
        response['Content-Length'] = os.path.getsize(path)
    else:
        response = HttpResponse()
        response['X-Accel-Redirect'] = secret_url

    response['Content-Type'] = "application/octet-stream"
    response['Content-Disposition'] = f"attachment; filename=\"{attachment_name}\""

    return response
