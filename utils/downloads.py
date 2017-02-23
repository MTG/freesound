
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
import stat
import zlib
import tempfile
import subprocess

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from sounds.models import License


def download_sounds(sounds_list, sounds_url, licenses_url=None):
    """
    From a list of sounds generates the HttpResponse with the information of
    the wav files of the sonds and a text file with the license. This response
    is handled by mod_zipfile of nginx to generate a zip file with the content.
    """
    users = User.objects.filter(sounds__in=sounds_list).distinct()
    # Generate text file with license info
    licenses = License.objects.all()
    attribution = render_to_string("sounds/pack_attribution.txt",
        dict(users=users,
            sounds_url=sounds_url,
            licenses=licenses,
            sound_list=sounds_list))

    tmpf = tempfile.NamedTemporaryFile(dir=settings.PACKS_PATH, delete=False)
    tmpf.write(attribution.encode("UTF-8"))
    tmpf.close()
    secret_name = tmpf.name.replace(settings.PACKS_PATH, settings.PACKS_SENDFILE_URL)

    os.chmod(tmpf.name, stat.S_IWUSR | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    license_crc = zlib.crc32(attribution.encode('UTF-8')) & 0xffffffff

    filelist = "%02x %i %s %s\r\n" % (license_crc,
                                    os.stat(tmpf.name).st_size,
                                    licenses_url, "_readme_and_license.txt")

    for sound in sounds_list:
        url = sound.locations("sendfile_url")
        name = sound.friendly_filename()
        if sound.crc == '':
            continue
        filelist += "%s %i %s %s\r\n" % (sound.crc, sound.filesize, url, name)


    response = HttpResponse(filelist, content_type="text/plain")
    response['X-Archive-Files'] = 'zip'
    return response
