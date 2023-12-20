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
import json
import logging

from django.conf import settings
from django.contrib.auth.models import User

from accounts.models import Profile, EmailPreferenceType
from follow import follow_utils
from utils.mail import render_mail_template
from utils.mail import send_mail
from utils.management_commands import LoggingBaseCommand

commands_logger = logging.getLogger("commands")
console_logger = logging.getLogger('console')


class Command(LoggingBaseCommand):
    """
    This command should be run periodically several times a day, and it will only send emails to users that "require it"
    """
    help = 'Send stream notifications to users who have not been notified for the last ' \
           'settings.NOTIFICATION_TIMEDELTA_PERIOD period and whose stream has new sounds for that period'
    args = True    # For backwards compatibility mode

    # See: http://stackoverflow.com/questions/30244288/django-management-command-cannot-see-arguments

    def handle(self, *args, **options):
        self.log_start()

        date_today_minus_notification_timedelta = datetime.datetime.now() - settings.NOTIFICATION_TIMEDELTA_PERIOD

        # Get all the users that have notifications active
        # and exclude the ones that have the last email sent for less than settings.NOTIFICATION_TIMEDELTA_PERIOD
        # (because they have been sent an email already)
        email_type = EmailPreferenceType.objects.get(name="stream_emails")
        user_ids = email_type.useremailsetting_set.values_list('user_id')

        users_enabled_notifications = Profile.objects.filter(user_id__in=user_ids).exclude(
            last_stream_email_sent__gt=date_today_minus_notification_timedelta
        ).order_by("-last_attempt_of_sending_stream_email")[:settings.MAX_EMAILS_PER_COMMAND_RUN]

        n_emails_sent = 0
        for profile in users_enabled_notifications:

            username = profile.user.username
            profile.last_attempt_of_sending_stream_email = datetime.datetime.now()

            # Variable names use the terminology "week" because settings.NOTIFICATION_TIMEDELTA_PERIOD defaults to a
            # week, but a more generic terminology could be used
            week_first_day = profile.last_stream_email_sent
            week_last_day = datetime.datetime.now()

            week_first_day_str = week_first_day.strftime("%d %b").lstrip("0")
            week_last_day_str = week_last_day.strftime("%d %b").lstrip("0")

            extra_email_subject = str(week_first_day_str) + ' to ' + str(week_last_day_str)

            # Set date range from which to get upload notifications
            time_lapse = follow_utils.build_time_lapse(week_first_day, week_last_day)

            # construct message
            user = User.objects.get(username=username)
            try:
                users_sounds, tags_sounds = follow_utils.get_stream_sounds(user, time_lapse)
            except Exception as e:
                # If error occur do not send the email
                console_logger.info(f"could not get new sounds data for {username.encode('utf-8')}")
                profile.save()    # Save last_attempt_of_sending_stream_email
                continue

            if not users_sounds and not tags_sounds:
                console_logger.info(f"no news sounds for {username.encode('utf-8')}")
                profile.save()    # Save last_attempt_of_sending_stream_email
                continue

            tvars = {'username': username, 'users_sounds': users_sounds, 'tags_sounds': tags_sounds}
            text_content = render_mail_template('emails/email_stream.txt', tvars)

            # Send email
            try:
                send_mail(
                    settings.EMAIL_SUBJECT_STREAM_EMAILS, text_content, extra_subject=extra_email_subject, user_to=user
                )
            except Exception as e:
                # Do not send the email and do not update the last email sent field in the profile
                profile.save()    # Save last_attempt_of_sending_stream_email
                commands_logger.info(
                    "Unexpected error while sending stream notification email (%s)" % json.dumps({
                        'email_to': profile.get_email_for_delivery(),
                        'username': profile.user.username,
                        'error': str(e)
                    })
                )
                continue
            n_emails_sent += 1

            # update last stream email sent date
            profile.last_stream_email_sent = datetime.datetime.now()
            profile.save()

        self.log_end({'n_users_notified': n_emails_sent})
