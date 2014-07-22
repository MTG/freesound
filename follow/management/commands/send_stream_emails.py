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
from django.core.mail import send_mass_mail

from django.core.management.base import BaseCommand
import settings
from utils.mail import send_mail_template, send_mass_html_mail, render_mail_template
from accounts.models import Profile
import datetime
import follow.utils
from django.contrib.auth.models import User
import sys

MAX_EMAILS_PER_RUN = 100

class Command(BaseCommand):
    args = ''
    help = 'Send stream new weekly sounds to users that are subscribed'

    def handle(self, *args, **options):

        date_week_before = datetime.datetime.now() - datetime.timedelta(days=7)

        # Get all the users that have notifications active
        # and exclude the ones that have the last email sent for less than 7 days
        # (because they have been sent an email already)
        users_enabled_notifications = Profile.objects.filter(enabled_stream_emails=True).exclude(last_stream_email_sent__gt=date_week_before).order_by("last_stream_email_sent")[:MAX_EMAILS_PER_RUN]

        print "Checking new sounds for", len(users_enabled_notifications), "users"
        print [str(profile.user.username) for profile in users_enabled_notifications]

        email_tuples = ()

        for profile in users_enabled_notifications:

            username = profile.user.username
            email_to = profile.user.email

            # construct subject
            week_first_day = profile.last_stream_email_sent
            week_last_day = datetime.datetime.now()

            # print week_first_day
            # print week_last_day

            week_first_day_str = week_first_day.strftime("%d %b").lstrip("0")
            week_last_day_str = week_last_day.strftime("%d %b").lstrip("0")

            # print week_first_day_str
            # print week_last_day_str

            subject_str = u'new sounds from users you are following ('
            subject_str += unicode(week_first_day_str) + u' - ' + unicode(week_last_day_str) + u')'

            # print subject_str

            # TODO: change this, this is only for test purposes
            time_lapse = "[2013-09-22T00:00:00Z TO 2014-07-02T23:59:59.999Z]"
            # time_lapse = follow.utils.build_time_lapse(week_first_day, week_last_day)

            # construct message
            user = User.objects.get(username=username)
            users_sounds, tags_sounds = follow.utils.get_stream_sounds(user, time_lapse)

            if not users_sounds and not tags_sounds:
                print "no news sounds for", username
                continue

            # print users_sound_ids
            # print tags_sound_ids

            text_content = render_mail_template('follow/email_stream.txt', locals())

            email_tuples += (subject_str, text_content, settings.DEFAULT_FROM_EMAIL, [email_to]),

            # update last stream email sent date
            # TODO: uncomment this later, for testing purposes only
            # profile.last_stream_email_sent = datetime.datetime.now()
            # profile.save()

        # mass email all messages
        send_mass_mail(email_tuples, fail_silently=False)