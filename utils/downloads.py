
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

import datetime
import zlib
from django.http import HttpResponse
from sounds.models import Download, PackDownload
from donations.models import DonationsModalSettings
import random


def download_sounds(licenses_url, pack):
    """
    From a list of sounds generates the HttpResponse with the information of
    the wav files of the sonds and a text file with the license. This response
    is handled by mod_zipfile of nginx to generate a zip file with the content.
    """
    attribution = pack.get_attribution()
    license_crc = zlib.crc32(attribution.encode('UTF-8')) & 0xffffffff
    filelist = "%02x %i %s %s\r\n" % (license_crc,
                                    len(attribution.encode('UTF-8')),
                                    licenses_url, "_readme_and_license.txt")

    sounds_list = pack.sounds.filter(processing_state="OK",
            moderation_state="OK").select_related('user', 'license')

    for sound in sounds_list:
        url = sound.locations("sendfile_url")
        name = sound.friendly_filename()
        if sound.crc == '':
            continue
        filelist += "%s %i %s %s\r\n" % (sound.crc, sound.filesize, url, name)

    response = HttpResponse(filelist, content_type="text/plain")
    response['X-Archive-Files'] = 'zip'
    return response


def should_suggest_donation(user, times_shown_in_last_day):
    """
    This method indicates when we should display the donation modal to the user. This will be based on 3 settings 
    indicating how many days after a donation we show the modal again, after how many downloads we display the modal 
    and for how long. The modal will be shown a maximum number of times per day.
    """

    donation_modal_settings = DonationsModalSettings.get_donation_modal_settings()

    if times_shown_in_last_day >= donation_modal_settings.max_times_display_a_day:
        # If modal has been shown more than settings.DONATION_MODAL_DISPLAY_TIMES_DAY times, don't show it again today
        return False

    if donation_modal_settings.never_show_modal_to_uploaders:
        if user.profile.num_sounds > 0:
            # Never show modal to users that have uploaded sounds
            return False

    donation_period = datetime.datetime.now() - datetime.timedelta(days=donation_modal_settings.days_after_donation)
    last_donation = user.donation_set.order_by('created').last()
    if not last_donation or last_donation.created < donation_period:
        # If there has never been a donation or last donation is older than settings.DONATION_MODAL_DAYS_AFTER_DONATION,
        # check if the number of downloads in the last settings.DONATION_MODAL_DOWNLOAD_DAYS days if bigger than
        # settings.DONATION_MODAL_DOWNLOADS_IN_PERIOD. If that is the case, show the modal.
        num_sound_downloads = Download.objects.filter(
            user=user,
            created__gt=datetime.datetime.now() - datetime.timedelta(days=donation_modal_settings.download_days)
        ).count()
        num_pack_downloads = PackDownload.objects.filter(
            user=user,
            created__gt=datetime.datetime.now() - datetime.timedelta(days=donation_modal_settings.download_days)
        ).count()
        num_downloads_in_period = num_sound_downloads + num_pack_downloads
        if num_downloads_in_period > donation_modal_settings.downloads_in_period:
            if random.random() <= donation_modal_settings.display_probability:
                return True
    return False
