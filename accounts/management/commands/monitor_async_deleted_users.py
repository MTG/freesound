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

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.admin import DELETE_SPAMMER_USER_ACTION_NAME, FULL_DELETE_USER_ACTION_NAME, \
    DELETE_USER_DELETE_SOUNDS_ACTION_NAME, DELETE_USER_KEEP_SOUNDS_ACTION_NAME
from accounts.models import Profile

logger = logging.getLogger('console')


class Command(BaseCommand):
    help = 'Gets a list of users that should have been asynchronously deleted recently and makes sure that these were' \
           'indeed deleted. The list of users is taken from Graylog "Delete user request" log messages.'

    def add_arguments(self, parser):

        parser.add_argument(
            '-n', '--n-days',
            action='store',
            dest='days',
            default=15,
            help='Number of days to search back for deletion requests')

    def handle(self, *args, **options):

        def get_messages_for_params(params):
            auth = (settings.GRAYLOG_USERNAME, settings.GRAYLOG_PASSWORD)
            r = requests.get(settings.GRAYLOG_DOMAIN + '/graylog/api/search/universal/relative/',
                             auth=auth, params=params, headers={'Accept': 'application/json'})
            response = r.json()
            if 'total_results' not in response:
                return -1, []
            return response['total_results'], response['messages']

        messages = []
        results_remaining = True
        messages_per_page = 150
        params = {
            'query': '"Requested async deletion of user"',
            'range': 60 * 60 * 24 * int(options['days']),
            'fields': 'message',
            'limit': messages_per_page,
            'offset': 0
        }

        while results_remaining:
            page = (params['offset'] / messages_per_page) + 1
            logger.info('Getting user delete requests info (page {0})'.format(page))

            try:
                total_results, new_messages = get_messages_for_params(params)
            except requests.HTTPError as e:
                logger.error(u"Can't access Graylog server. Error: {}".format(e))
                break

            messages += new_messages
            params['offset'] += messages_per_page

            if len(messages) >= total_results:
                # If we already obtained all messages, break while
                results_remaining = False

        users_not_properly_deleted = []
        for message in messages:
            msg = message['message']['message']
            user_id = int(msg.split('Requested async deletion of user ')[1].split(' - '))

            if DELETE_SPAMMER_USER_ACTION_NAME in msg:
                if User.objects.filter(id=user_id).exists():
                    # If user object still exists with that id, action was not properly taken
                    users_not_properly_deleted.append((user_id, 'User object deletion was requested because of being '
                                                                'spammer, but User object still exists'))

            elif DELETE_USER_DELETE_SOUNDS_ACTION_NAME in msg:
                if Profile.objects.filter(user_id=user_id, is_anonymized_user=False).exists():
                    # If user object still exists with that id and is not anonymized, action was not properly taken
                    # Note that we use Profile objects as a proxy for User
                    users_not_properly_deleted.append((user_id, 'User anonymization (with sound deletion) was '
                                                                'requested, but Profile object is not '
                                                                'marked as such'))

            elif DELETE_USER_KEEP_SOUNDS_ACTION_NAME in msg:
                if Profile.objects.filter(user_id=user_id, is_anonymized_user=False).exists():
                    # If user object still exists with that id and is not anonymized, action was not properly taken
                    # Note that we use Profile objects as a proxy for User
                    users_not_properly_deleted.append((user_id, 'User anonymization (preserving sounds) was '
                                                                'requested, but Profile object is not '
                                                                'marked as such'))

            elif FULL_DELETE_USER_ACTION_NAME:
                if User.objects.filter(id=user_id).exists():
                    # If user object still exists with that id, action was not properly taken
                    users_not_properly_deleted.append((user_id, 'User object full deletion was requested, '
                                                                'but User object still exists'))

        if not users_not_properly_deleted:
            logger.info('All {0} delete users requests were carried out successfully'.format(len(messages)))
        else:
            message_to_log = 'The following {0} delete users requests seem to have failed\n'\
                .format(len(users_not_properly_deleted))
            for user_id, error_message in users_not_properly_deleted:
                message_to_log += '- {0}: {1}\n'.format(user_id, error_message)
            logger.info(message_to_log)
