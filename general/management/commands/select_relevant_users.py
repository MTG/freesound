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

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.conf import settings
from optparse import make_option
import time, json, os, sys
from datetime import date

settings.DEBUG = False


class Command(BaseCommand):
    """Select relevant active users and write a JSON list of these users to a file.
    """
    help = '''Select relevant active users and write a JSON list of these users to a file.'''
    args = '''[<limit> <since> <sounds> <output>]'''

    option_list = BaseCommand.option_list + (
        make_option('--limit', action='store', dest='limit', default=100,
                    help='Limit the number of users.'),
        make_option('--since', action='store', dest='since', default='2010-6-1',
                    help='Only select users that have logged in since this date (yyyy-(m)m-(d)d).'),
        make_option('--sounds', action='store', dest='sounds', default=100,
                    help='Only select users that have uploaded more than this number of sounds.'),
        make_option('--output', action='store', dest='output', default='/tmp/relevant_users.json',
                    help='Write the JSON list of selected users to this file.')
    )

    def handle(self, *args, **options):

        tic = time.clock()

        qs = User.objects.raw("""
SELECT id
FROM auth_user
WHERE last_login >= '%s'
AND id IN ( SELECT user_id
            FROM sounds_sound
            GROUP BY user_id
            HAVING COUNT(user_id) > %s
            ORDER BY COUNT(user_id) DESC )
LIMIT %s
""" % \
(options['since'], options['sounds'], options['limit']))

        users = [{'sounds': user.sounds.all().count(),
                  'email': user.email,
                  'id': user.id,
                  'username': user.username} for user in qs]

        with open(options['output'], mode='w') as f:
            json.dump(users, f)

        toc = time.clock()

        self.stdout.write('\n\n')
        self.stdout.write("Selecting at most %s users active since %s with more than %s sounds.\n" % \
                          (options['limit'], options['since'], options['sounds']))
        self.stdout.write("%s users selected " % str(len(users)))
        self.stdout.write('(performed in ' + str(toc-tic) + ' seconds)\n')
        self.stdout.write("The JSON representation of the select users was written to: \n\t%s\n" % \
                          options['output'])
        self.stdout.flush()
