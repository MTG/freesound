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
from django.contrib.contenttypes.models import ContentType
from optparse import make_option
from sounds.models import Sound, Pack
from comments.models import Comment
from accounts.models import Profile
from pprint import pprint
import sys


class Command(BaseCommand):
    help = "This command checks if 'count' properties of Profiles, Sounds and Packs and in sync with the actual " \
           "number of existing objects (e.g. if pack.num_sounds equals pack.sounds.all().count(). If the number" \
           "does not match, it updates the corresponding object (unless the option -n is provided)"

    option_list = BaseCommand.option_list + (
        make_option('-n', '--no-changes',
                    dest='no-changes',
                    action='store_true',
                    default=False,
                    help='Using the option --no-changes the original objects will not be modified.'),
    )

    def handle(self,  *args, **options):

        sound_content_type = ContentType.objects.get_for_model(Sound)

        # Iterate over all sounds to check: num_comments, num_downloads, avg_rating, num_ratings
        # While iterating, we keep a list of user ids and pack ids for then iterating over them
        all_user_ids = set()
        all_pack_ids = set()
        mismatches_report = {
            'Sound.num_comments': 0,
            'Sound.num_downloads': 0,
            'Sound.avg_rating': 0,
            'Sound.num_ratings': 0,
            'Pack.num_sounds': 0,
            'Pack.num_downloads': 0,
            'User.num_sounds': 0,
            'User.num_posts': 0,
        }
        print "Iterating over existing sounds...",
        total = Sound.objects.all().count()
        for count, sound in enumerate(Sound.objects.all().iterator()):
            # Collect user and pack data for later use
            all_user_ids.add(sound.user_id)
            if sound.pack:
                all_pack_ids.add(sound.pack_id)

            # Check num_comments
            real_num_comments = Comment.objects.filter(object_id=sound.id, content_type=sound_content_type).count()
            if real_num_comments != sound.num_comments:
                mismatches_report['Sound.num_comments'] += 1
                if not options['no-changes']:
                    sound.num_comments = real_num_comments
                    sound.save()

            # TODO: check num_downloads, num_ratings, avg_rating

            # Report progress
            if count % 1000 == 0:
                sys.stdout.write("\rIterating over existing sounds... %.2f" % (100 * float(count)/total))
                sys.stdout.flush()
        print " done!"

        # TODO: iterate over users
        # TODO: iterate over packs

        print "\nNumber of mismatched counts: "
        pprint(mismatches_report)
