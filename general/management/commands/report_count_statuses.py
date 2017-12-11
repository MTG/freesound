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


import sys
from pprint import pprint

from django.core.management.base import BaseCommand
from django.db.models import Count, Avg
from django.contrib.auth.models import User

from sounds.models import Sound, Pack
from forum.models import Post


class Command(BaseCommand):
    help = "This command checks if 'count' properties of Profiles, Sounds and Packs and in sync with the actual " \
           "number of existing objects (e.g. if pack.num_sounds equals pack.sounds.all().count(). If the number" \
           "does not match, it updates the corresponding object (unless the option -n is provided)"

    def add_arguments(self, parser):
        parser.add_argument(
            '-n', '--no-changes',
            action='store_true',
            dest='no-changes',
            default=False,
            help='Using the option --no-changes the original objects will not be modified.')
        parser.add_argument(
            '-d', '--skip-downloads',
            action='store_true',
            dest='skip-downloads',
            default=False,
            help='Using the option --skip-downloads the command will not checked for mismatched downloads '
                 '(to save time).')

    def handle(self,  *args, **options):

        def report_progress(message, total, count):
            if count % 100 == 0:
                sys.stdout.write(
                    '\r' + message % (total, 100 * float(count + 1) / total))
                sys.stdout.flush()
            if count + 1 == total:
                print 'done!'

        # Iterate over all sounds to check: num_comments, num_downloads, avg_rating, num_ratings
        # While iterating, we keep a list of user ids and pack ids for then iterating over them

        mismatches_report = {
            'Sound.num_comments': 0,
            'Sound.num_downloads': 0,
            'Sound.num_ratings': 0,
            'Pack.num_sounds': 0,
            'Pack.num_downloads': 0,
            'User.num_sounds': 0,
            'User.num_posts': 0,
        }
        mismatches_object_ids = {
            'Sound.num_comments': list(),
            'Sound.num_downloads': list(),
            'Sound.num_ratings': list(),
            'Pack.num_sounds': list(),
            'Pack.num_downloads': list(),
            'User.num_sounds': list(),
            'User.num_posts': list(),
        }

        # IMPLEMENTATION NOTE: on the code below we iterate multiple times on Sounds, Packs and Users tables.
        # This is done in this way because using the Django ORM we can't annotate counts from different tables in a
        # single queryset (annotations that would require SQL JOINs with more than one table). If we do that, we
        # get wrong results for the annotated fields as the generated SQL duplicates results for each table (see
        # https://code.djangoproject.com/ticket/10060).

        # Sounds
        total = Sound.objects.all().count()

        # Look at number of comments
        for count, sound in enumerate(Sound.objects.all().annotate(real_num_comments=Count('comments')).iterator()):
            real_num_comments = sound.real_num_comments
            if real_num_comments != sound.num_comments:
                mismatches_report['Sound.num_comments'] += 1
                mismatches_object_ids['Sound.num_comments'].append(sound.id)
                sound.num_comments = real_num_comments
                if not options['no-changes']:
                    sound.is_index_dirty = True
                    sound.save()
            report_progress('Checking number of comments in %i sounds... %.2f%%', total, count)

        # Look at number of rartings and average rating
        for count, sound in enumerate(Sound.objects.all().annotate(
                real_num_ratings=Count('ratings'), real_avg_rating=Avg('ratings__rating')).iterator()):
            real_num_ratings = sound.real_num_ratings
            if real_num_ratings != sound.num_ratings:
                mismatches_report['Sound.num_ratings'] += 1
                mismatches_object_ids['Sound.num_ratings'].append(sound.id)
                sound.num_ratings = real_num_ratings
                sound.avg_rating = sound.real_avg_rating
                if not options['no-changes']:
                    sound.is_index_dirty = True
                    sound.save()
            report_progress('Checking number and average of ratings in %i sounds... %.2f%%', total, count)

        # Look at number of downloads
        if not options['skip-downloads']:
            for count, sound in enumerate(Sound.objects.all().annotate(
                    real_num_downloads=Count('downloads')).iterator()):

                real_num_downloads = sound.real_num_downloads
                if real_num_downloads != sound.num_downloads:
                    mismatches_report['Sound.num_downloads'] += 1
                    mismatches_object_ids['Sound.num_downloads'].append(sound.id)
                    sound.num_downloads = real_num_downloads
                    if not options['no-changes']:
                        sound.is_index_dirty = True
                        sound.save()
                report_progress('Checking number of downloads in %i sounds... %.2f%%', total, count)

        # Packs
        total = Pack.objects.all().count()

        # Look at number of sounds
        for count, pack in enumerate(Pack.objects.all().extra(select={
            'real_num_sounds': """
                SELECT COUNT(U0."id") AS "count"
                FROM "sounds_sound" U0
                WHERE U0."pack_id" = ("sounds_pack"."id") 
                AND U0."processing_state" = 'OK' AND U0."moderation_state" = 'OK'
            """
        }).iterator()):
            real_num_sounds = pack.real_num_sounds
            if real_num_sounds != pack.num_sounds:
                mismatches_report['Pack.num_sounds'] += 1
                mismatches_object_ids['Pack.num_sounds'].append(pack.id)
                pack.num_sounds = real_num_sounds
                if not options['no-changes']:
                    pack.save()
            report_progress("Checking number of sounds in %i packs... %.2f%%", total, count)

        # Look at number of downloads
        if not options['skip-downloads']:
            for count, pack in enumerate(Pack.objects.all().annotate(real_num_downloads=Count('downloads')).iterator()):
                real_num_downloads = pack.real_num_downloads
                if real_num_downloads != pack.real_num_sounds:
                    mismatches_report['Pack.num_downloads'] += 1
                    mismatches_object_ids['Pack.num_downloads'].append(pack.id)
                    pack.num_downloads = real_num_downloads
                    if not options['no-changes']:
                        pack.save()
                report_progress("Checking number of downloads in %i packs... %.2f%%", total, count)

        # Users
        potential_user_ids = set()
        potential_user_ids.update(Sound.objects.all().values_list('user_id', flat=True))  # Add ids of uploaders
        potential_user_ids.update(Post.objects.all().values_list('author_id', flat=True))  # Add ids of forum posters
        total = len(potential_user_ids)

        # Look at number of sounds
        for count, user in enumerate(User.objects.filter(id__in=potential_user_ids).select_related('profile').extra(
                select={
                    'real_num_sounds': """
                        SELECT COUNT(U0."id") AS "count"
                        FROM "sounds_sound" U0
                        WHERE U0."user_id" = ("auth_user"."id") 
                        AND U0."processing_state" = 'OK' AND U0."moderation_state" = 'OK'
                    """
                }).iterator()):
            user_profile = user.profile
            real_num_sounds = user.real_num_sounds
            if real_num_sounds != user_profile.num_sounds:
                mismatches_report['User.num_sounds'] += 1
                mismatches_object_ids['User.num_sounds'].append(user.id)
                user_profile.num_sounds = real_num_sounds
                if not options['no-changes']:
                    user_profile.save()
            report_progress('Checking number of sounds in %i users... %.2f%%', total, count)

        # Look at number of posts
        for count, user in enumerate(User.objects.filter(id__in=potential_user_ids).select_related('profile').annotate(
                real_num_posts=Count('posts'),).iterator()):
            user_profile = user.profile
            real_num_posts = user.real_num_posts
            if real_num_posts != user_profile.num_posts:
                mismatches_report['User.num_posts'] += 1
                mismatches_object_ids['User.num_posts'].append(user.id)
                user_profile.num_posts = real_num_posts
                if not options['no-changes']:
                    user_profile.save()
            report_progress('Checking number of posts in %i users... %.2f%%', total, count)

        print "\nNumber of mismatched counts: "
        pprint(mismatches_report)
        mismatches_object_ids = {key:value for key, value in mismatches_object_ids.items() if value}
        pprint(mismatches_object_ids)
